import os
import glob
import re

pattern = re.compile(r'(\w+)\.setStyleSheet\s*\((.*?)\)', re.DOTALL)
files = glob.glob('ui/**/*.py', recursive=True) + glob.glob('ui/*.py')

for py in files:
    with open(py, encoding='utf-8') as f:
        content = f.read()
    for m in pattern.finditer(content):
        var, style = m.group(1), m.group(2).strip()
        # Look for container-like variables
        if any(w in var.lower() for w in ['container', 'frame', 'card', 'box', 'panel', 'col', 'row', 'bar', 'dialog', 'widget']):
            single_line_style = " ".join(style.split())[:80]
            print(f"{os.path.basename(py)}: {var} -> {single_line_style}")
