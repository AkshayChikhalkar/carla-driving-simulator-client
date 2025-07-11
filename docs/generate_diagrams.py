#!/usr/bin/env python3
"""
Script to generate PNG images from Mermaid diagrams.
This script converts all .mmd files in the mmd/ directory to PNG images.
"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

def check_mermaid_cli():
    """Check if mermaid-cli is installed."""
    try:
        # Try to find mmdc in PATH
        mmdc_path = shutil.which('mmdc')
        if mmdc_path:
            subprocess.run([mmdc_path, '--version'], capture_output=True, check=True)
            return True
        return False
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_mermaid_cli():
    """Install mermaid-cli using npm."""
    print("Installing mermaid-cli...")
    try:
        # Try to find npm in PATH
        npm_path = shutil.which('npm')
        if not npm_path:
            print("Error: npm not found in PATH")
            print("Please ensure Node.js and npm are properly installed")
            return False
        
        print(f"Using npm at: {npm_path}")
        subprocess.run([npm_path, 'install', '-g', '@mermaid-js/mermaid-cli'], check=True)
        print("mermaid-cli installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install mermaid-cli: {e}")
        return False
    except FileNotFoundError as e:
        print(f"npm not found: {e}")
        print("Please install Node.js from https://nodejs.org/")
        return False

def generate_diagrams():
    """Generate PNG images from Mermaid diagrams."""
    # Get the project root directory (two levels up from docs/)
    project_root = Path(__file__).parent.parent
    mmd_dir = project_root / 'mmd'
    output_dir = Path(__file__).parent / '_static' / 'images'
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all .mmd files
    mmd_files = list(mmd_dir.glob('*.mmd'))
    
    if not mmd_files:
        print(f"No .mmd files found in {mmd_dir}")
        return
    
    print(f"Found {len(mmd_files)} Mermaid diagram files")
    
    # Find mmdc executable
    mmdc_path = shutil.which('mmdc')
    if not mmdc_path:
        print("Error: mmdc not found in PATH after installation")
        return
    
    # Convert each file
    for mmd_file in mmd_files:
        output_file = output_dir / f"{mmd_file.stem}.png"
        print(f"Converting {mmd_file.name} to {output_file.name}...")
        
        try:
            subprocess.run([
                mmdc_path,
                '-i', str(mmd_file),
                '-o', str(output_file),
                '-b', 'transparent'
            ], check=True)
            print(f"✓ Successfully generated {output_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to convert {mmd_file.name}: {e}")

def main():
    """Main function."""
    print("Mermaid Diagram Generator")
    print("=" * 30)
    
    # Check if mermaid-cli is installed
    if not check_mermaid_cli():
        print("mermaid-cli not found. Attempting to install...")
        if not install_mermaid_cli():
            print("\nPlease install mermaid-cli manually:")
            print("npm install -g @mermaid-js/mermaid-cli")
            print("\nOr use the Windows batch file: docs/generate_diagrams.bat")
            sys.exit(1)
    
    # Generate diagrams
    generate_diagrams()
    print("\nDiagram generation completed!")

if __name__ == '__main__':
    main() 