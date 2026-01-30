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
    // Simple validation: token must be non-empty and look like a JWT (3 parts separated by dots)
    let parts: Vec<&str> = token.split('.').collect();
    parts.len() == 3 && parts.iter().all(|p| !p.is_empty())
}

fn main() {
    let server = Server::http("0.0.0.0:25566").expect("Failed to bind to port 25566");
    println!("Minecraft log server listening on port 25566");
    
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
