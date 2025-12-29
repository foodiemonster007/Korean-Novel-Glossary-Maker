#!/usr/bin/env python3
"""
Setup script for Novel Glossary Maker
Checks Python version, installs required packages, and verifies installations
"""
import sys
import subprocess
import platform
import os
from pathlib import Path

# Define minimum Python version
REQUIRED_PYTHON = (3, 8, 0)

# Define required packages with minimum versions
REQUIRED_PACKAGES = [
    ("pandas", "1.5.0"),
    ("google-genai", "1.0.0"),
    ("opencc-python-reimplemented", "0.1.7"),
    ("xlsxwriter", "3.0.0"),
    ("plyer", "2.0.0"),
    ("openpyxl", "3.1.0"),
    ("packaging", "21.0"),
    ("tkinter", None),  # Usually comes with Python
]

def check_python_version():
    """Check if Python version meets requirements."""
    print("=" * 60)
    print("Checking Python version...")
    print(f"Current Python version: {sys.version}")
    
    current_version = sys.version_info[:3]
    
    if current_version < REQUIRED_PYTHON:
        print(f"❌ Error: Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ is required.")
        print(f"   You have Python {current_version[0]}.{current_version[1]}.{current_version[2]}")
        print("   Please upgrade your Python installation.")
        return False
    else:
        print(f"✅ Python version check passed ({current_version[0]}.{current_version[1]}.{current_version[2]})")
        return True

def check_tkinter():
    """Check if tkinter is available."""
    try:
        import tkinter
        print("✅ tkinter is available")
        return True
    except ImportError:
        print("❌ tkinter is not available")
        
        # Platform-specific installation instructions
        system = platform.system()
        if system == "Windows":
            print("   On Windows, tkinter should be included with Python.")
            print("   If missing, try reinstalling Python with the 'tcl/tk and IDLE' option checked.")
        elif system == "Darwin":  # macOS
            print("   On macOS, install tkinter with: brew install python-tk")
        elif system == "Linux":
            print("   On Linux, install tkinter with:")
            print("     Ubuntu/Debian: sudo apt-get install python3-tk")
            print("     Fedora/RHEL: sudo dnf install python3-tkinter")
            print("     Arch: sudo pacman -S tk")
        return False

def check_package(package_name, min_version=None):
    """Check if a package is installed and meets minimum version requirement."""
    try:
        # Special handling for tkinter
        if package_name == "tkinter":
            return check_tkinter()
        
        # Special handling for packages where import name differs from package name
        import_mapping = {
            "google-genai": "genai",
            "opencc-python-reimplemented": "opencc"
        }
        
        # Get the actual module name to import
        module_name = import_mapping.get(package_name, package_name)
        
        # Import the package
        module = __import__(module_name)
        
        # Check version if specified
        if min_version and hasattr(module, '__version__'):
            current_version = module.__version__
            from packaging import version
            
            if version.parse(current_version) < version.parse(min_version):
                print(f"⚠️  {package_name} version {current_version} is below required {min_version}")
                return False
            else:
                print(f"✅ {package_name} {current_version} (minimum: {min_version})")
        else:
            print(f"✅ {package_name} is installed")
        return True
        
    except ImportError:
        print(f"❌ {package_name} is not installed")
        return False
    except Exception as e:
        print(f"⚠️  Error checking {package_name}: {e}")
        return False

def install_package(package_name, version=None):
    """Install or upgrade a package using pip."""
    try:
        if version:
            package_spec = f"{package_name}>={version}"
        else:
            package_spec = package_name
        
        print(f"Installing {package_spec}...")
        
        # Use subprocess to call pip
        cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package_spec]
        
        # For tkinter on Linux, we need different commands
        if package_name == "tkinter":
            print("   Note: tkinter may require system package manager to install.")
            return True
        
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        if result.returncode == 0:
            print(f"✅ Successfully installed {package_spec}")
            return True
        else:
            print(f"❌ Failed to install {package_spec}")
            if result.stderr:
                print(f"   Error: {result.stderr[:200]}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_spec}")
        print(f"   Error: {e.stderr[:200] if e.stderr else str(e)}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error installing {package_spec}: {e}")
        return False

def create_requirements_file():
    """Create a requirements.txt file for future use."""
    requirements_content = ""
    for package, version in REQUIRED_PACKAGES:
        if package == "tkinter":
            continue  # Skip tkinter from requirements.txt
        if version:
            requirements_content += f"{package}>={version}\n"
        else:
            requirements_content += f"{package}\n"
    
    with open("requirements.txt", "w") as f:
        f.write(requirements_content)
    
    print("✅ Created requirements.txt file")

def check_optional_packages():
    """Check for optional packages that enhance functionality."""
    print("\n" + "=" * 60)
    print("Checking optional packages...")
    
    optional_packages = [
        ("tqdm", "4.65.0", "Progress bars for long operations"),
        ("colorama", "0.4.6", "Colored terminal output"),
        ("pytest", "7.4.0", "Testing framework"),
    ]
    
    for package, version, description in optional_packages:
        try:
            __import__(package)
            print(f"✅ {package} - {description}")
        except ImportError:
            print(f"⚠️  {package} not installed - {description}")

def setup_environment():
    """Main setup function."""
    print("=" * 60)
    print("NOVEL GLOSSARY MAKER - SETUP")
    print("=" * 60)
    
    # Check Python version first
    if not check_python_version():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Checking required packages...")
    
    # Check and install required packages
    packages_to_install = []
    
    for package_name, min_version in REQUIRED_PACKAGES:
        if not check_package(package_name, min_version):
            packages_to_install.append((package_name, min_version))
    
    # Install missing packages
    if packages_to_install:
        print("\n" + "=" * 60)
        print("Installing missing packages...")
        
        # First, make sure pip is up to date
        print("Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      capture_output=True, text=True)
        
        # Install packaging module first if needed for version comparisons
        try:
            import packaging
        except ImportError:
            print("Installing packaging module for version checks...")
            install_package("packaging", "21.0")
        
        # Install missing packages
        failed_installs = []
        for package_name, min_version in packages_to_install:
            if not install_package(package_name, min_version):
                failed_installs.append(package_name)
        
        if failed_installs:
            print(f"\n❌ Failed to install: {', '.join(failed_installs)}")
            print("   Please install them manually with:")
            for package in failed_installs:
                print(f"     pip install {package}")
            return False
        return True
    
    # Create requirements file
    create_requirements_file()
    
    # Check optional packages
    check_optional_packages()
    
    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        success = setup_environment()
        
        if success:    
            print("\n" + "=" * 60)
            print("SETUP SUCCESSFUL!")
            print("=" * 60)
            print("\nTo run the application, use:")
            print("  • python GLOSSARY_MAKER.py")
            
        else:
            print("\n" + "=" * 60)
            print("SETUP FAILED!")
            print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        import traceback
        traceback.print_exc()
    
    # Keep command prompt open
    print("\n" + "=" * 60)
    input("Press Enter to close this window...")