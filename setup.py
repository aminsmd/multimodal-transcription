#!/usr/bin/env python3
"""
Setup script for the standalone transcription pipeline.

This script helps set up the environment and install dependencies.
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✓ Python version: {sys.version}")
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed."""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✓ FFmpeg is installed")
            return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    print("✗ FFmpeg is not installed or not in PATH")
    print("Please install FFmpeg:")
    print("  - macOS: brew install ffmpeg")
    print("  - Ubuntu/Debian: sudo apt install ffmpeg")
    print("  - Windows: Download from https://ffmpeg.org/download.html")
    return False

def install_dependencies():
    """Install Python dependencies."""
    print("Installing Python dependencies...")
    
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True)
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def check_google_api_key():
    """Check if Google API key is set."""
    api_key = os.getenv('GOOGLE_API_KEY')
    if api_key:
        print("✓ GOOGLE_API_KEY is set")
        return True
    else:
        print("✗ GOOGLE_API_KEY is not set")
        print("Please set your Google API key:")
        print("  export GOOGLE_API_KEY='your_api_key_here'")
        print("  or create a .env file with: GOOGLE_API_KEY=your_api_key_here")
        return False

def create_env_template():
    """Create a .env template file."""
    env_template = """# Google API Key for Gemini
GOOGLE_API_KEY=your_api_key_here

# Optional: Custom output directory
# OUTPUT_DIR=outputs
"""
    
    env_path = Path(".env.template")
    with open(env_path, 'w') as f:
        f.write(env_template)
    
    print(f"✓ Created .env.template file")
    print("Copy this to .env and add your API key")

def run_tests():
    """Run the test suite."""
    print("Running tests...")
    
    try:
        result = subprocess.run([sys.executable, 'test_pipeline.py'], 
                              capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print("✓ All tests passed")
            return True
        else:
            print(f"✗ Tests failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print("✗ Tests timed out")
        return False
    except Exception as e:
        print(f"✗ Test execution failed: {e}")
        return False

def main():
    """Main setup function."""
    print("=" * 60)
    print("STANDALONE TRANSCRIPTION PIPELINE SETUP")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("src/transcription_pipeline.py").exists():
        print("Error: Please run this script from the standalone_transcription_pipeline directory")
        return 1
    
    # Run checks
    checks = [
        ("Python Version", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("Dependencies", install_dependencies),
        ("Google API Key", check_google_api_key)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        print(f"\n--- {check_name} ---")
        if not check_func():
            all_passed = False
    
    # Create environment template
    print("\n--- Environment Template ---")
    create_env_template()
    
    # Run tests if everything else passed
    if all_passed:
        print("\n--- Running Tests ---")
        if run_tests():
            print("\n🎉 Setup completed successfully!")
            print("\nNext steps:")
            print("1. Set your GOOGLE_API_KEY in .env file")
            print("2. Run: python src/transcription_pipeline.py --input your_video.mp4")
            print("3. Check examples/ directory for usage examples")
        else:
            print("\n⚠️  Setup completed but tests failed")
            print("Please check the error messages above")
    else:
        print("\n❌ Setup failed")
        print("Please fix the issues above and run setup again")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
