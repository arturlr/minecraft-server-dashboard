use std::process::Command;
use std::env;
use std::collections::HashMap;
use tiny_http::{Server, Response, Method, Header};
use jsonwebtoken::{decode, decode_header, DecodingKey, Validation, Algorithm};
use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize)]
struct Claims {
    sub: String,
    email: Option<String>,
    exp: usize,
    #[serde(rename = "cognito:username")]
    cognito_username: Option<String>,
}

#[derive(Debug, Deserialize)]
struct Jwk {
    kid: String,
    kty: String,
    n: String,
    e: String,
}

#[derive(Debug, Deserialize)]
struct JwkSet {
    keys: Vec<Jwk>,
}

fn get_jwks(region: &str, user_pool_id: &str) -> Result<JwkSet, Box<dyn std::error::Error>> {
    let url = format!(
        "https://cognito-idp.{}.amazonaws.com/{}/.well-known/jwks.json",
        region, user_pool_id
    );
    
    let response = reqwest::blocking::get(&url)?;
    let jwks: JwkSet = response.json()?;
    Ok(jwks)
}

fn validate_token(token: &str, region: &str, user_pool_id: &str, jwks: &JwkSet) -> Result<Claims, Box<dyn std::error::Error>> {
    // Get the key ID from token header
    let header = decode_header(token)?;
    let kid = header.kid.ok_or("No kid in token header")?;
    
    // Find the matching key
    let jwk = jwks.keys.iter()
        .find(|k| k.kid == kid)
        .ok_or("No matching key found")?;
    
    // Decode the RSA components
    let n = base64::decode_config(&jwk.n, base64::URL_SAFE_NO_PAD)?;
    let e = base64::decode_config(&jwk.e, base64::URL_SAFE_NO_PAD)?;
    
    // Create decoding key
    let decoding_key = DecodingKey::from_rsa_components(&n, &e)?;
    
    // Validate token
    let mut validation = Validation::new(Algorithm::RS256);
    validation.set_audience(&[user_pool_id]);
    
    let token_data = decode::<Claims>(token, &decoding_key, &validation)?;
    
    Ok(token_data.claims)
}

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

fn main() {
    let region = env::var("AWS_REGION").unwrap_or_else(|_| "us-west-2".to_string());
    let user_pool_id = env::var("COGNITO_USER_POOL_ID")
        .expect("COGNITO_USER_POOL_ID environment variable must be set");
    
    // Fetch JWKS at startup
    let jwks = match get_jwks(&region, &user_pool_id) {
        Ok(jwks) => jwks,
        Err(e) => {
            eprintln!("Failed to fetch JWKS: {}", e);
            std::process::exit(1);
        }
    };
    
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
                            if validate_token(token, &region, &user_pool_id, &jwks).is_ok() {
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
