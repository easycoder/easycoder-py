#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/home/graham/dev/easycoder/easycoder-py')
os.chdir('/home/graham/dev/easycoder/easycoder-py/tests')

# Import the handler directly
from ec_doclets import Doclets, DocletManager

# Test the DocletManager directly
print("=" * 70)
print("Testing DocletManager directly")
print("=" * 70)

manager = DocletManager(doclets_dir='~/Doclets/Doclets,~/Doclets/EasyCoder,~/Doclets/RBR')

print("\n" + "=" * 70)
print("Finding all doclets...")
print("=" * 70)
doclets = manager.find_all_doclets()
print(f"\nTotal doclets found: {len(doclets)}")
for filepath, filename, subject in doclets[:5]:
    print(f"  - {filename}: {subject}")

print("\n" + "=" * 70)
print("Searching for 'api'...")
print("=" * 70)
results = manager.search_data('api')
print(f"Results: {len(results)} matches")
for r in results:
    print(f"  - {r['display_filename']}: {r['subject']}")
