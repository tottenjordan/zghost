#!/usr/bin/env python3

import subprocess
import sys
import os

def run_command(command, check=True):
    """Run a shell command and return the result."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=check,
            capture_output=True,
            text=True
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr

def install_ffmpeg():
    """Install ffmpeg on Ubuntu."""
    print("Installing ffmpeg on Ubuntu...")
    
    # Check if running with sudo or as root
    if os.geteuid() != 0:
        print("This script requires sudo privileges. Please run with sudo.")
        sys.exit(1)
    
    # Update package list
    print("Updating package list...")
    success, stdout, stderr = run_command("apt-get update")
    if not success:
        print(f"Failed to update package list: {stderr}")
        sys.exit(1)
    
    # Install ffmpeg
    print("Installing ffmpeg...")
    success, stdout, stderr = run_command("apt-get install -y ffmpeg")
    if not success:
        print(f"Failed to install ffmpeg: {stderr}")
        sys.exit(1)
    
    # Verify installation
    print("Verifying installation...")
    success, stdout, stderr = run_command("ffmpeg -version", check=False)
    if success:
        print("ffmpeg installed successfully!")
        print(stdout.split('\n')[0])  # Print first line of version info
    else:
        print("ffmpeg installation failed!")
        sys.exit(1)

if __name__ == "__main__":
    install_ffmpeg()