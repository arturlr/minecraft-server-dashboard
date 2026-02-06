use std::fs::File;
use std::io::{BufRead, BufReader};
use std::path::Path;
use tiny_http::{Server, Response, Method, Header};
use jsonwebtoken::{decode, DecodingKey, Validation, Algorithm};
use serde::{Deserialize, Serialize};

const MAX_LINES: usize = 1000;
const MAX_FILE_SIZE: u64 = 100 * 1024 * 1024; // 100MB

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    instance_id: String,
}

fn get_minecraft_logs(log_path: &str, lines: usize) -> Result<String, String> {
    let safe_lines = lines.min(MAX_LINES);
    let path = Path::new(log_path);
    
    if !path.exists() {
        return Err("Log file not found".to_string());
    }
    
    // Check file size to prevent memory exhaustion
    let metadata = std::fs::metadata(path)
        .map_err(|_| "Cannot read log file metadata".to_string())?;
    
    if metadata.len() > MAX_FILE_SIZE {
        return Err("Log file too large".to_string());
    }
    
    let file = File::open(path)
        .map_err(|_| "Cannot open log file".to_string())?;
    
    let reader = BufReader::new(file);
    
    // Use VecDeque for efficient tail operation
    let mut lines_buffer: std::collections::VecDeque<String> = std::collections::VecDeque::with_capacity(safe_lines);
    
    for line in reader.lines() {
        if let Ok(line_content) = line {
            if lines_buffer.len() >= safe_lines {
                lines_buffer.pop_front();
            }
            lines_buffer.push_back(line_content);
        }
    }
    
    Ok(lines_buffer.into_iter().collect::<Vec<_>>().join("\n"))
}

fn parse_query_param(url: &str, param: &str) -> Option<String> {
    url.split('?')
        .nth(1)?
        .split('&')
        .find_map(|pair| {
            let mut parts = pair.split('=');
            if parts.next()? == param {
                parts.next().map(|v| v.to_string())
            } else {
                None
            }
        })
}

fn validate_token(token: &str, jwt_secret: &str) -> bool {
    // Validate JWT secret strength
    if jwt_secret.len() < 32 {
        eprintln!("Warning: JWT secret is too short (minimum 32 characters)");
        return false;
    }
    
    let key = DecodingKey::from_secret(jwt_secret.as_ref());
    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = false; // Allow tokens without expiration for now
    
    match decode::<Claims>(token, &key, &validation) {
        Ok(token_data) => {
            // Validate required fields are non-empty
            !token_data.claims.sub.is_empty() && !token_data.claims.instance_id.is_empty()
        }
        Err(e) => {
            eprintln!("JWT validation failed: {}", e);
            false
        }
    }
}

fn main() {
    let port = std::env::var("LOG_SERVICE_PORT").unwrap_or_else(|_| "25566".to_string());
    let bind_addr = format!("0.0.0.0:{}", port);
    
    let log_path = std::env::var("LOG_FILE_PATH")
        .unwrap_or_else(|_| "/logs/latest.log".to_string());
    
    // Try to read JWT secret from Docker secrets first, then environment variable
    let jwt_secret = std::fs::read_to_string("/run/secrets/jwt_secret")
        .ok()
        .map(|s| s.trim().to_string())
        .or_else(|| std::env::var("JWT_SECRET").ok())
        .expect("JWT_SECRET must be set via environment variable or Docker secret");
    
    // Validate JWT secret strength
    if jwt_secret.len() < 32 {
        eprintln!("ERROR: JWT_SECRET must be at least 32 characters long");
        std::process::exit(1);
    }
    
    let server = Server::http(&bind_addr)
        .unwrap_or_else(|_| panic!("Failed to bind to {}", bind_addr));
    
    println!("Minecraft log server listening on {}", bind_addr);
    println!("Reading logs from: {}", log_path);
    
    for request in server.incoming_requests() {
        let url = request.url().to_string();
        let method = request.method().clone();
        
        match (&method, url.as_str()) {
            (&Method::Get, url) if url.starts_with("/logs") => {
                // Extract and validate JWT token
                let mut authorized = false;
                for header in request.headers() {
                    if header.field.equiv("Authorization") {
                        let auth_value = header.value.as_str();
                        if let Some(token) = auth_value.strip_prefix("Bearer ") {
                            if validate_token(token, &jwt_secret) {
                                authorized = true;
                                break;
                            }
                        }
                    }
                }
                
                if !authorized {
                    eprintln!("Unauthorized access attempt to /logs");
                    let response = Response::from_string("Unauthorized")
                        .with_status_code(401);
                    let _ = request.respond(response);
                    continue;
                }
                
                let lines = parse_query_param(&url, "lines")
                    .and_then(|n| n.parse::<usize>().ok())
                    .unwrap_or(100)
                    .min(MAX_LINES);
                
                match get_minecraft_logs(&log_path, lines) {
                    Ok(logs) => {
                        let response = Response::from_string(logs)
                            .with_header(Header::from_bytes(&b"Content-Type"[..], &b"text/plain"[..]).unwrap());
                        let _ = request.respond(response);
                    }
                    Err(e) => {
                        eprintln!("Error reading logs: {}", e);
                        let response = Response::from_string("Error reading logs")
                            .with_status_code(500);
                        let _ = request.respond(response);
                    }
                }
            }
            (&Method::Get, "/health") => {
                let response = Response::from_string("OK")
                    .with_status_code(200);
                let _ = request.respond(response);
            }
            _ => {
                let response = Response::from_string("Use GET /logs?lines=100 or GET /health")
                    .with_status_code(404);
                let _ = request.respond(response);
            }
        }
    }
}
