#!/usr/bin/env python3
"""
N_m3u8DL-RE installer for YUNA-System.
Automatically downloads and installs N_m3u8DL-RE binary.
"""

import os
import sys
import platform
import subprocess
import tempfile
import shutil
import logging
from pathlib import Path
from urllib.request import urlopen
from urllib.error import URLError

from yuna.utils.logging import get_logger

logger = get_logger(__name__)


class Nm3u8Installer:
    """Installer for N_m3u8DL-RE binary."""
    
    # GitHub release information
    GITHUB_API = "https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest"
    
    # Installation directories
    INSTALL_DIRS = [
        "/usr/local/bin",
        "/usr/bin",
        os.path.expanduser("~/.local/bin"),
        os.getcwd(),
    ]
    
    def __init__(self, install_dir: str = None):
        """
        Initialize installer.
        
        Args:
            install_dir: Target installation directory (auto-detected if None)
        """
        self.install_dir = install_dir
        self.system = platform.system().lower()
        self.arch = platform.machine().lower()
        
        # Normalize architecture names
        if self.arch in ["x86_64", "amd64"]:
            self.arch = "x64"
        elif self.arch in ["aarch64", "arm64"]:
            self.arch = "arm64"
        elif self.arch in ["armv7l", "armv6l"]:
            self.arch = "arm"
        else:
            self.arch = "x64"  # Default fallback
            
    def get_download_url(self) -> tuple[str, str]:
        """
        Get download URL and filename for current platform.
        
        Returns:
            Tuple of (download_url, filename)
        """
        # Map platforms to release assets
        platform_map = {
            ("linux", "x64"): ("linux-x64", "N_m3u8DL-RE"),
            ("linux", "arm64"): ("linux-arm64", "N_m3u8DL-RE"),
            ("linux", "arm"): ("linux-arm", "N_m3u8DL-RE"),
            ("windows", "x64"): ("win-x64", "N_m3u8DL-RE.exe"),
            ("windows", "arm64"): ("win-arm64", "N_m3u8DL-RE.exe"),
            ("darwin", "x64"): ("osx-x64", "N_m3u8DL-RE"),
            ("darwin", "arm64"): ("osx-arm64", "N_m3u8DL-RE"),
        }
        
        key = (self.system, self.arch)
        if key not in platform_map:
            raise RuntimeError(f"Unsupported platform: {self.system}-{self.arch}")
            
        platform_name, binary_name = platform_map[key]
        
        # Get latest release info
        try:
            with urlopen(self.GITHUB_API, timeout=10) as response:
                import json
                release_data = json.loads(response.read().decode())
                version = release_data["tag_name"].lstrip("v")
                
                # Find the matching asset
                asset_pattern = f"N_m3u8DL-RE_{platform_name}_{'net' if self.system == 'linux' else ''}.zip"
                
                for asset in release_data["assets"]:
                    if asset_pattern in asset["name"]:
                        return asset["browser_download_url"], binary_name
                        
                raise RuntimeError(f"Could not find release asset for {platform_name}")
                
        except (URLError, json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to get release info: {e}")
            raise RuntimeError("Failed to fetch release information from GitHub")
            
    def find_install_dir(self) -> str:
        """
        Find appropriate installation directory.
        
        Returns:
            Installation directory path
        """
        if self.install_dir:
            return self.install_dir
            
        # Check existing directories in PATH
        path_dirs = os.environ.get("PATH", "").split(os.pathsep)
        for dir_path in self.INSTALL_DIRS:
            if dir_path in path_dirs and os.access(dir_path, os.W_OK):
                return dir_path
                
        # Check writable directories
        for dir_path in self.INSTALL_DIRS:
            if os.path.exists(dir_path) and os.access(dir_path, os.W_OK):
                return dir_path
                
        # Fallback to current directory
        return os.getcwd()
        
    def install(self) -> bool:
        """
        Download and install N_m3u8DL-RE.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Installing N_m3u8DL-RE...")
            
            # Get download URL
            download_url, binary_name = self.get_download_url()
            logger.info(f"Downloading from: {download_url}")
            
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Download zip file
                zip_path = os.path.join(temp_dir, "download.zip")
                logger.info(f"Downloading to: {zip_path}")
                
                with urlopen(download_url, timeout=60) as response:
                    with open(zip_path, "wb") as f:
                        shutil.copyfileobj(response, f)
                        
                # Extract zip
                logger.info("Extracting...")
                import zipfile
                with zipfile.ZipFile(zip_path, "r") as zip_ref:
                    zip_ref.extractall(temp_dir)
                    
                # Find the binary
                binary_path = None
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file == binary_name or file == "N_m3u8DL-RE":
                            binary_path = os.path.join(root, file)
                            break
                    if binary_path:
                        break
                        
                if not binary_path:
                    raise RuntimeError("Binary not found in extracted archive")
                    
                # Make executable (Unix systems)
                if self.system != "windows":
                    os.chmod(binary_path, 0o755)
                    
                # Install to target directory
                install_dir = self.find_install_dir()
                target_path = os.path.join(install_dir, "N_m3u8DL-RE")
                
                logger.info(f"Installing to: {target_path}")
                shutil.move(binary_path, target_path)
                
                # Verify installation
                if os.path.exists(target_path):
                    logger.info("✅ N_m3u8DL-RE installed successfully!")
                    logger.info(f"Path: {target_path}")
                    
                    # Check if directory is in PATH
                    if install_dir not in os.environ.get("PATH", "").split(os.pathsep):
                        logger.warning(f"⚠️  {install_dir} is not in PATH")
                        logger.warning(f"Add it to your PATH or use: export PATH=$PATH:{install_dir}")
                        
                    return True
                else:
                    raise RuntimeError("Installation failed - binary not found after install")
                    
        except Exception as e:
            logger.error(f"❌ Installation failed: {e}")
            return False
            
    def check_installed(self) -> bool:
        """
        Check if N_m3u8DL-RE is already installed.
        
        Returns:
            True if installed, False otherwise
        """
        try:
            result = subprocess.run(
                ["N_m3u8DL-RE", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False


def install_nm3u8(force: bool = False, install_dir: str = None) -> bool:
    """
    Install N_m3u8DL-RE binary.
    
    Args:
        force: Force installation even if already installed
        install_dir: Target installation directory
        
    Returns:
        True if successful, False otherwise
    """
    installer = Nm3u8Installer(install_dir)
    
    # Check if already installed
    if not force and installer.check_installed():
        logger.info("✅ N_m3u8DL-RE is already installed")
        return True
        
    # Install
    return installer.install()


def main():
    """Command line interface for installer."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Install N_m3u8DL-RE for YUNA-System")
    parser.add_argument("--force", action="store_true", help="Force reinstallation")
    parser.add_argument("--dir", help="Installation directory")
    parser.add_argument("--check", action="store_true", help="Check if already installed")
    
    args = parser.parse_args()
    
    if args.check:
        installer = Nm3u8Installer()
        if installer.check_installed():
            print("✅ N_m3u8DL-RE is installed and working")
            sys.exit(0)
        else:
            print("❌ N_m3u8DL-RE is not installed or not working")
            sys.exit(1)
            
    success = install_nm3u8(force=args.force, install_dir=args.dir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()