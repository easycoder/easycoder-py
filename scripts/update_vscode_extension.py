#!/usr/bin/env python3
"""
Update VS Code extension syntax highlighting with keywords from EasyCoder source files.
Extracts keywords from ec_core.py and ec_pyside.py and updates the tmLanguage.json file.
"""

import re
import json
import os
from pathlib import Path

def extract_keywords_from_file(filepath):
    """Extract keyword definitions (k_xxx methods) from a Python file."""
    keywords = set()
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find all k_xxx method definitions
    pattern = r'def k_(\w+)\(self'
    matches = re.findall(pattern, content)
    
    for match in matches:
        keywords.add(match)
    
    return keywords

def main():
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Source files to extract keywords from
    source_files = [
        project_root / 'easycoder' / 'ec_core.py',
        project_root / 'easycoder' / 'ec_pyside.py'
    ]
    
    # Collect all keywords
    all_keywords = set()
    
    for source_file in source_files:
        if source_file.exists():
            keywords = extract_keywords_from_file(source_file)
            print(f"Found {len(keywords)} keywords in {source_file.name}")
            all_keywords.update(keywords)
        else:
            print(f"Warning: {source_file} not found")
    
    # Sort keywords alphabetically
    sorted_keywords = sorted(all_keywords)
    
    print(f"\nTotal unique keywords: {len(sorted_keywords)}")
    print(f"Keywords: {', '.join(sorted_keywords)}")
    
    # Update the tmLanguage.json file
    syntax_file = project_root / '.vscode' / 'easycoder' / 'syntaxes' / 'easycoder.tmLanguage.json'
    
    if not syntax_file.exists():
        print(f"\nError: Syntax file not found at {syntax_file}")
        return 1
    
    # Read the current syntax file
    with open(syntax_file, 'r') as f:
        syntax_data = json.load(f)
    
    # Create the keyword pattern (regex alternation)
    keyword_pattern = '\\b(' + '|'.join(sorted_keywords) + ')\\b'
    
    # Update the keywords pattern
    # Find the keyword.control.easycoder pattern and update it
    for pattern in syntax_data['repository']['keywords']['patterns']:
        if pattern.get('name') == 'keyword.control.easycoder':
            old_pattern = pattern['match']
            pattern['match'] = keyword_pattern
            print(f"\nUpdated keyword pattern in {syntax_file.name}")
            print(f"Old: {old_pattern[:80]}...")
            print(f"New: {keyword_pattern[:80]}...")
            break
    
    # Write back the updated syntax file
    with open(syntax_file, 'w') as f:
        json.dump(syntax_data, f, indent=2)
    
    print(f"\n✓ Successfully updated {syntax_file}")
    print("\nTo apply changes:")
    print("1. Restart VS Code, or")
    print("2. Run 'Developer: Reload Window' from the Command Palette")
    
    return 0

if __name__ == '__main__':
    exit(main())
