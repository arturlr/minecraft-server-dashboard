use std::process::Command;
use tiny_http::{Server, Response, Method, Header};

fn get_minecraft_logs(lines: usize) -> String {
    let safe_lines = lines.min(1000);
    
    let output = Command::new("journalctl")
        .arg("-u")
        .arg("minecraft")
        .arg("-n")
        .arg(safe_lines.to_string())
        .arg("--no-pager")
        .output();
    
    match output {
        Ok(out) => String::from_utf8_lossy(&out.stdout).to_string(),
        Err(e) => format!("Error fetching logs: {}", e),
    }
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

fn validate_token(token: &str) -> bool {
    // Decode base64 token and validate structure
    use base64::{Engine as _, engine::general_purpose};
    
    let decoded = match general_purpose::STANDARD.decode(token) {
        Ok(d) => d,
        Err(_) => return false,
    };
    
    let json_str = match std::str::from_utf8(&decoded) {
        Ok(s) => s,
        Err(_) => return false,
    };
    
    // Parse JSON and check for required fields
    let parsed: serde_json::Value = match serde_json::from_str(json_str) {
        Ok(p) => p,
        Err(_) => return false,
    };
    
    // Validate required fields exist and are non-empty
    if let (Some(sub), Some(instance_id)) = (parsed.get("sub"), parsed.get("instance_id")) {
        sub.is_string() && instance_id.is_string() 
            && !sub.as_str().unwrap().is_empty() 
            && !instance_id.as_str().unwrap().is_empty()
    } else {
        false
    }
}

fn main() {
    let port = std::env::var("LOG_SERVICE_PORT").unwrap_or_else(|_| "25566".to_string());
    let bind_addr = format!("0.0.0.0:{}", port);
    
    let server = Server::http(&bind_addr)
        .unwrap_or_else(|_| panic!("Failed to bind to {}", bind_addr));
    
    println!("Minecraft log server listening on {}", bind_addr);
    
    for request in server.incoming_requests() {
        match (request.method(), request.url()) {
            (&Method::Get, url) if url.starts_with("/logs") => {
                // Extract and validate JWT token
                let mut authorized = false;
                for header in request.headers() {
                    if header.field.equiv("Authorization") {
                        let auth_value = header.value.as_str();
                        if let Some(token) = auth_value.strip_prefix("Bearer ") {
                            if validate_token(token) {
                                authorized = true;
                                break;
                            }
                        }
                    }
                }
                
                if !authorized {
                    let response = Response::from_string("Unauthorized")
                        .with_status_code(401);
                    let _ = request.respond(response);
                    continue;
                }
                
                let lines = parse_query_param(url, "lines")
                    .and_then(|n| n.parse::<usize>().ok())
                    .unwrap_or(100)
                    .min(1000);
                
                let logs = get_minecraft_logs(lines);
                let response = Response::from_string(logs)
                    .with_header(Header::from_bytes(&b"Content-Type"[..], &b"text/plain"[..]).unwrap());
                
                let _ = request.respond(response);
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
