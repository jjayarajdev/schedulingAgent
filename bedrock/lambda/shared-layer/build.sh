#!/bin/bash

# ============================================================================
# Lambda Layer Build Script
# Builds shared Lambda layer for Bedrock Agents
# ============================================================================

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================================"
echo "Building Shared Lambda Layer"
echo "============================================================================"

# Clean previous build
echo "Cleaning previous build..."
rm -rf build/
rm -f shared-layer.zip

# Create build directory
echo "Creating build directory..."
mkdir -p build/python/lib

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt -t build/python/ --upgrade

# Copy library code
echo "Copying library code..."
cp -r python/lib/* build/python/lib/

# Create zip file
echo "Creating layer zip file..."
cd build
zip -r ../shared-layer.zip python/ -q

cd ..

# Show size
echo ""
echo "Build complete!"
echo "Layer size: $(du -h shared-layer.zip | cut -f1)"
echo "Location: $SCRIPT_DIR/shared-layer.zip"
echo ""
echo "============================================================================"
echo "To deploy this layer to AWS Lambda:"
echo ""
echo "  aws lambda publish-layer-version \\"
echo "    --layer-name bedrock-agent-shared \\"
echo "    --description 'Shared utilities for Bedrock Agents' \\"
echo "    --zip-file fileb://shared-layer.zip \\"
echo "    --compatible-runtimes python3.11 python3.12 \\"
echo "    --region us-east-1"
echo ""
echo "============================================================================"
