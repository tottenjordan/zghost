#!/usr/bin/env python3

import subprocess
import sys
import os
import logging
import platform
import shutil

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

def check_ffmpeg_installed():
    """Check if ffmpeg is already installed."""
    return shutil.which("ffmpeg") is not None

def get_ffmpeg_version():
    """Get the installed ffmpeg version."""
    success, stdout, stderr = run_command("ffmpeg -version", check=False)
    if success and stdout:
        return stdout.split('\n')[0]
    return None

def install_ffmpeg():
    """Install or verify ffmpeg installation."""
    logger = logging.getLogger(__name__)
    system = platform.system()
    
    # First check if ffmpeg is already installed
    if check_ffmpeg_installed():
        version = get_ffmpeg_version()
        if version:
            logger.info(f"ffmpeg is already installed: {version}")
        else:
            logger.info("ffmpeg is already installed")
        return
    
    logger.info(f"ffmpeg not found. Attempting to install on {system}...")
    
    if system == "Linux":
        # Check if we can use snap (doesn't require sudo)
        if shutil.which("snap"):
            logger.info("Attempting to install ffmpeg via snap (no sudo required)...")
            success, stdout, stderr = run_command("snap install ffmpeg", check=False)
            if success:
                logger.info("ffmpeg installed successfully via snap!")
                return
        
        # Check for conda/mamba
        if shutil.which("conda"):
            logger.info("Attempting to install ffmpeg via conda (no sudo required)...")
            success, stdout, stderr = run_command("conda install -y -c conda-forge ffmpeg", check=False)
            if success:
                logger.info("ffmpeg installed successfully via conda!")
                return
        
        # Provide instructions for manual installation
        logger.warning("Unable to install ffmpeg automatically without sudo.")
        logger.info("Please install ffmpeg using one of these methods:")
        logger.info("  1. With sudo: sudo apt-get install ffmpeg")
        logger.info("  2. With snap: snap install ffmpeg")
        logger.info("  3. With conda: conda install -c conda-forge ffmpeg")
        logger.info("  4. Download static build: https://johnvansickle.com/ffmpeg/")
        
    elif system == "Darwin":  # macOS
        if shutil.which("brew"):
            logger.info("Attempting to install ffmpeg via Homebrew...")
            success, stdout, stderr = run_command("brew install ffmpeg", check=False)
            if success:
                logger.info("ffmpeg installed successfully via Homebrew!")
                return
        
        logger.warning("Unable to install ffmpeg automatically.")
        logger.info("Please install ffmpeg using Homebrew: brew install ffmpeg")
        logger.info("Or download from: https://evermeet.cx/ffmpeg/")
        
    elif system == "Windows":
        logger.warning("Automatic installation not supported on Windows.")
        logger.info("Please download ffmpeg from: https://www.gyan.dev/ffmpeg/builds/")
        logger.info("Or use chocolatey: choco install ffmpeg")
        
    else:
        logger.warning(f"Unsupported system: {system}")
        logger.info("Please install ffmpeg manually for your system.")

if __name__ == "__main__":
    # Configure logging for standalone execution
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    install_ffmpeg()