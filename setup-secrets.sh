#!/bin/bash
# Setup Docker secrets for Minecraft Dashboard
# This script generates secure random secrets for RCON and JWT authentication

set -e

SECRETS_DIR="./secrets"

echo "Setting up Docker secrets..."

# Create secrets directory
mkdir -p "$SECRETS_DIR"

# Generate RCON password (32 bytes = 256 bits)
echo "Generating RCON password..."
openssl rand -base64 32 > "$SECRETS_DIR/rcon_password.txt"

# Generate JWT secret (32 bytes = 256 bits)
echo "Generating JWT secret..."
openssl rand -base64 32 > "$SECRETS_DIR/jwt_secret.txt"

# Set secure permissions
chmod 600 "$SECRETS_DIR"/*
chmod 700 "$SECRETS_DIR"

echo "✅ Secrets generated successfully!"
echo ""
echo "Files created:"
echo "  - $SECRETS_DIR/rcon_password.txt"
echo "  - $SECRETS_DIR/jwt_secret.txt"
echo ""
echo "⚠️  IMPORTANT: Never commit these files to version control!"
echo "⚠️  Add 'secrets/' to .gitignore"
echo ""
echo "To view secrets:"
echo "  cat $SECRETS_DIR/rcon_password.txt"
echo "  cat $SECRETS_DIR/jwt_secret.txt"
