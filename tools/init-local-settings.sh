#!/bin/bash

# Initialize local.settings.json for Azure Functions API
# This script creates a local.settings.json if it doesn't exist
# Safe to run multiple times - won't overwrite existing files

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="$SCRIPT_DIR/.."
API_DIR="$WORKSPACE_DIR/api"
LOCAL_SETTINGS_FILE="$API_DIR/local.settings.json"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Initializing local.settings.json ===${NC}"

# Rename .sln file to match workspace name (first run only)
WORKSPACE_NAME=$(basename "$WORKSPACE_DIR")
EXISTING_SLN=$(find "$WORKSPACE_DIR" -maxdepth 1 -name "*.sln" -type f | head -n 1)
if [ -n "$EXISTING_SLN" ] && [ "$(basename "$EXISTING_SLN")" != "${WORKSPACE_NAME}.sln" ]; then
    NEW_SLN="$WORKSPACE_DIR/${WORKSPACE_NAME}.sln"
    mv "$EXISTING_SLN" "$NEW_SLN"
    echo -e "${GREEN}✓ Renamed solution file to ${WORKSPACE_NAME}.sln${NC}"
fi

# Check if local.settings.json already exists
if [ -f "$LOCAL_SETTINGS_FILE" ]; then
    echo -e "${YELLOW}local.settings.json already exists, skipping creation${NC}"
    exit 0
fi

# Create local.settings.json with Azurite connection string
cat > "$LOCAL_SETTINGS_FILE" << 'EOF'
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "dotnet-isolated",
    "STORAGE": "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;QueueEndpoint=http://127.0.0.1:10001/devstoreaccount1;TableEndpoint=http://127.0.0.1:10002/devstoreaccount1;"
  }
}
EOF

echo -e "${GREEN}✓ Created local.settings.json with Azurite configuration${NC}"
echo -e "  File: $LOCAL_SETTINGS_FILE"
echo -e "\n${YELLOW}Note: This file uses Azurite (local storage emulator)${NC}"
echo -e "To use Azure Storage, update the connection strings in local.settings.json"
