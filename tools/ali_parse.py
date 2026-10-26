"""Pull 'title | price | sold' lines out of a saved AliExpress snapshot."""
import glob, os, re, sys
f = sys.argv[1] if len(sys.argv) > 1 else max(glob.glob(os.path.expanduser(
    "~/.claude/projects/*neurband*/*/tool-results/mcp-backplane-preview_snapshot-*.txt")), key=os.path.getmtime)
t = open(f).read().replace('\\n', '\n')
seen = set()
for m in re.finditer(r'name": ?"([^"]{20,240}?) \| (€[\d.,]+)(?: \| €[\d.,]+)?(?: \| \((€[\d.,]+/pc)\))?(?: \| ([\d.]+))?(?: \| ([\d,+]+ sold))?', t):
    title = m.group(1)
    if title in seen: continue
    seen.add(title)
    print(f"{m.group(2):>8} {m.group(3) or '':>12} {m.group(5) or '':>12}  {title[:150]}")
