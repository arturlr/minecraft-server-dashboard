#!/bin/bash
set -e

RUN_COMMAND="$1"
WORK_DIR="/opt/minecraft"
MINECRAFT_VERSION="${2:-1.21.4}"  # Default to 1.21.4, can be overridden

if [ -z "$RUN_COMMAND" ]; then
    echo "Usage: $0 <run-command> [minecraft-version]"
    exit 1
fi

echo "=== Setting up Minecraft directory ==="
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Check if server.jar exists, if not download it
if [ ! -f "server.jar" ]; then
    echo "Minecraft server.jar not found, downloading version $MINECRAFT_VERSION..."
    
    # Fetch version manifest to get download URL
    VERSION_MANIFEST=$(curl -s "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json")
    
    # Validate JSON response
    if ! echo "$VERSION_MANIFEST" | jq empty 2>/dev/null; then
        echo "Error: Invalid JSON response from Mojang API"
        exit 1
    fi
    
    VERSION_URL=$(echo "$VERSION_MANIFEST" | jq -r ".versions[] | select(.id==\"$MINECRAFT_VERSION\") | .url" | head -1)
    
    if [ -z "$VERSION_URL" ] || [ "$VERSION_URL" = "null" ]; then
        echo "Warning: Version $MINECRAFT_VERSION not found, using latest release"
        VERSION_URL=$(echo "$VERSION_MANIFEST" | jq -r '.versions[] | select(.type=="release") | .url' | head -1)
    fi
    
    # Validate URL format
    if [[ ! "$VERSION_URL" =~ ^https://piston-meta\.mojang\.com/ ]]; then
        echo "Error: Invalid version URL from Mojang API"
        exit 1
    fi
    
    # Get server download URL
    VERSION_DATA=$(curl -s "$VERSION_URL")
    
    # Validate JSON response
    if ! echo "$VERSION_DATA" | jq empty 2>/dev/null; then
        echo "Error: Invalid JSON response from version manifest"
        exit 1
    fi
    
    SERVER_URL=$(echo "$VERSION_DATA" | jq -r '.downloads.server.url')
    SERVER_SHA1=$(echo "$VERSION_DATA" | jq -r '.downloads.server.sha1')
    
    if [ -z "$SERVER_URL" ] || [ "$SERVER_URL" = "null" ]; then
        echo "Error: Could not fetch server download URL"
        exit 1
    fi
    
    # Validate URL format
    if [[ ! "$SERVER_URL" =~ ^https://piston-data\.mojang\.com/ ]]; then
        echo "Error: Invalid server download URL"
        exit 1
    fi
    
    # Download server.jar
    wget -O server.jar "$SERVER_URL"
    
    # Verify checksum if available
    if [ -n "$SERVER_SHA1" ] && [ "$SERVER_SHA1" != "null" ]; then
        DOWNLOADED_SHA1=$(sha1sum server.jar | awk '{print $1}')
        if [ "$DOWNLOADED_SHA1" != "$SERVER_SHA1" ]; then
            echo "Error: Checksum verification failed"
            rm server.jar
            exit 1
        fi
        echo "✓ Checksum verified"
    fi
    
    echo "eula=true" > eula.txt
    echo "✓ Minecraft server downloaded"
else
    echo "✓ Minecraft server.jar already exists"
fi

echo "=== Setting up Minecraft systemd service ==="

# Create dedicated minecraft user if it doesn't exist
if ! id -u minecraft >/dev/null 2>&1; then
    useradd -r -m -d /opt/minecraft -s /bin/bash minecraft
    echo "✓ Created minecraft user"
fi

# Set ownership
chown -R minecraft:minecraft "$WORK_DIR"

# Extract the actual java command from the run command (remove screen/sudo wrapper)
JAVA_COMMAND=$(echo "$RUN_COMMAND" | sed 's/.*screen //; s/sudo //')

# If no run command provided or server.jar doesn't exist in command, use default
if [[ ! "$JAVA_COMMAND" =~ server\.jar ]]; then
    echo "Using default Java command with 2GB memory allocation"
    JAVA_COMMAND="java -Xms2G -Xmx2G -jar server.jar nogui"
fi

cat > /etc/systemd/system/minecraft.service <<EOF
[Unit]
Description=Minecraft Server
After=network.target

[Service]
Type=simple
User=minecraft
Group=minecraft
WorkingDirectory=$WORK_DIR
ExecStart=/bin/bash -c '$JAVA_COMMAND'
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable minecraft.service

echo "✓ Minecraft service created and enabled"
echo "Starting Minecraft service..."
if systemctl start minecraft.service; then
    echo "✓ Minecraft service started successfully"
    systemctl status minecraft.service --no-pager
else
    echo "✗ Failed to start Minecraft service"
    echo "Checking logs..."
    journalctl -u minecraft.service -n 20 --no-pager
    exit 1
fi
