#!/bin/bash

# Install ffmpeg on Ubuntu
# This script installs ffmpeg and its dependencies

set -e

echo "Installing ffmpeg on Ubuntu..."

# Update package list
apt-get update

# Install ffmpeg
apt-get install -y ffmpeg

# Verify installation
if command -v ffmpeg &> /dev/null; then
    echo "ffmpeg installed successfully!"
    ffmpeg -version
else
    echo "ffmpeg installation failed!"
    exit 1
fi