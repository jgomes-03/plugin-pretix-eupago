#!/usr/bin/env python
"""
This script updates version numbers in various files to match the version in apps.py.
Run this script whenever you change the version number in apps.py.
"""

import os
import re

# Get the root directory of the plugin
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(script_dir))  # Go up two directories from the scripts folder

# Get version from apps.py
def get_version():
    with open(os.path.join(root_dir, 'eupago', 'apps.py'), encoding='utf-8') as f:
        content = f.read()
        match = re.search(r"__version__\s*=\s*'([^']+)'", content)
        if match:
            return match.group(1)
        raise RuntimeError("Unable to find version string.")

# Update version in README.md
def update_readme_version(version):
    readme_path = os.path.join(root_dir, 'README.md')
    
    with open(readme_path, encoding='utf-8') as f:
        content = f.read()
    
    # Update the version in the header
    new_content = re.sub(
        r'^(## Versão) .*',
        r'\1 ' + version,
        content,
        flags=re.MULTILINE
    )
    
    if content != new_content:
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Updated version in README.md to {version}")
    else:
        print("Version in README.md already up to date")

if __name__ == '__main__':
    version = get_version()
    print(f"Current version: {version}")
    update_readme_version(version)
    
    print("\nAll files updated successfully!")
    print(f"EuPago plugin version is now {version} in all files.")
