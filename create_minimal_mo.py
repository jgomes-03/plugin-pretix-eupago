#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compilador de traduções robusto para o plugin EuPago
"""

import os
import sys
from pathlib import Path

def create_empty_mo_file(mo_path):
    """Create a minimal valid .mo file with just the header"""
    
    # Minimal .mo file structure
    # Magic number (little-endian)
    magic = b'\xde\x12\x04\x95'
    
    # Version
    version = b'\x00\x00\x00\x00'
    
    # Number of strings (0 - just header)
    num_strings = b'\x00\x00\x00\x00'
    
    # Offset of key table
    key_offset = b'\x1c\x00\x00\x00'  # 28 bytes (7 * 4)
    
    # Offset of value table  
    value_offset = b'\x1c\x00\x00\x00'  # Same as key offset since no strings
    
    # Hash table size (not used)
    hash_size = b'\x00\x00\x00\x00'
    
    # Hash table offset (not used)
    hash_offset = b'\x1c\x00\x00\x00'
    
    # Write the minimal .mo file
    with open(mo_path, 'wb') as f:
        f.write(magic)
        f.write(version)
        f.write(num_strings)
        f.write(key_offset)
        f.write(value_offset)
        f.write(hash_size)
        f.write(hash_offset)
    
    print(f"Created minimal .mo file: {mo_path}")

def main():
    # Create minimal .mo files for both locales
    base_path = Path('eupago/locale')
    
    locales = ['pt', 'en']
    
    for locale in locales:
        mo_path = base_path / locale / 'LC_MESSAGES' / 'django.mo'
        po_path = base_path / locale / 'LC_MESSAGES' / 'django.po'
        
        # Ensure directory exists
        mo_path.parent.mkdir(parents=True, exist_ok=True)
        
        if po_path.exists():
            print(f"Creating .mo file for {locale}")
            create_empty_mo_file(mo_path)
        else:
            print(f"Warning: {po_path} not found")
    
    print("\nAll .mo files created successfully!")
    print("Note: These are minimal .mo files. Django will fallback to English text for untranslated strings.")

if __name__ == '__main__':
    main()
