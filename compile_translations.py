#!/usr/bin/env python3
"""
Simple script to compile .po files to .mo files without external dependencies
"""

import struct
import array
from pathlib import Path

def make_mo(po_path, mo_path):
    """Convert .po file to .mo file"""
    
    # Read the .po file
    with open(po_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse messages
    messages = {}
    current_msgid = None
    current_msgstr = None
    in_msgid = False
    in_msgstr = False
    
    for line in content.split('\n'):
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith('#'):
            continue
            
        if line.startswith('msgid '):
            if current_msgid is not None and current_msgstr is not None:
                if current_msgid and current_msgstr:  # Don't add empty translations
                    messages[current_msgid] = current_msgstr
            # Extract msgid content
            current_msgid = line[6:].strip('"')
            current_msgstr = None
            in_msgid = True
            in_msgstr = False
            
        elif line.startswith('msgstr '):
            # Extract msgstr content  
            current_msgstr = line[7:].strip('"')
            in_msgid = False
            in_msgstr = True
            
        elif line.startswith('"') and line.endswith('"'):
            # Continuation line
            content_line = line[1:-1]  # Remove quotes
            if in_msgid and current_msgid is not None:
                current_msgid += content_line
            elif in_msgstr and current_msgstr is not None:
                current_msgstr += content_line
    
    # Don't forget the last message
    if current_msgid is not None and current_msgstr is not None:
        if current_msgid and current_msgstr:
            messages[current_msgid] = current_msgstr
    
    # Create .mo file
    keys = sorted(messages.keys())
    
    # Calculate offsets
    koffsets = []
    voffsets = []
    kencoded = []
    vencoded = []
    
    for key in keys:
        kencoded.append(key.encode('utf-8'))
        vencoded.append(messages[key].encode('utf-8'))
    
    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart
    for k in kencoded:
        valuestart += len(k)
    
    koffsets = []
    voffsets = []
    
    # Key offsets
    offset = keystart
    for k in kencoded:
        koffsets.append(offset)
        offset += len(k)
    
    # Value offsets  
    offset = valuestart
    for v in vencoded:
        voffsets.append(offset)
        offset += len(v)
    
    # Write .mo file
    with open(mo_path, 'wb') as f:
        # Magic number
        f.write(struct.pack('<I', 0x950412de))
        # Version
        f.write(struct.pack('<I', 0))
        # Number of entries
        f.write(struct.pack('<I', len(keys)))
        # Offset of key table
        f.write(struct.pack('<I', 7 * 4))
        # Offset of value table  
        f.write(struct.pack('<I', 7 * 4 + 8 * len(keys)))
        # Hash table size (not used)
        f.write(struct.pack('<I', 0))
        # Hash table offset (not used)
        f.write(struct.pack('<I', 0))
        
        # Key table
        for i, key in enumerate(keys):
            f.write(struct.pack('<I', len(kencoded[i])))
            f.write(struct.pack('<I', koffsets[i]))
            
        # Value table
        for i, key in enumerate(keys):
            f.write(struct.pack('<I', len(vencoded[i])))
            f.write(struct.pack('<I', voffsets[i]))
            
        # Keys
        for k in kencoded:
            f.write(k)
            
        # Values
        for v in vencoded:
            f.write(v)

if __name__ == '__main__':
    # Compile Portuguese translations
    po_pt = Path('eupago/locale/pt/LC_MESSAGES/django.po')
    mo_pt = Path('eupago/locale/pt/LC_MESSAGES/django.mo')
    
    if po_pt.exists():
        make_mo(po_pt, mo_pt)
        print(f"Compiled {po_pt} -> {mo_pt}")
    
    # Compile English translations
    po_en = Path('eupago/locale/en/LC_MESSAGES/django.po')
    mo_en = Path('eupago/locale/en/LC_MESSAGES/django.mo')
    
    if po_en.exists():
        make_mo(po_en, mo_en)
        print(f"Compiled {po_en} -> {mo_en}")
    else:
        print(f"File not found: {po_en}")
