"""Print AliExpress search results (title + price) from the newest saved browser snapshot."""
import glob, os, re
f = max(glob.glob(os.path.expanduser("~/.claude/projects/*neurband*/*/tool-results/mcp-backplane-preview_snapshot-*.txt")), key=os.path.getmtime)
t = open(f).read().replace('\\n', '\n').replace('\\"', '"')
for m in dict.fromkeys(re.findall(r'link "Report fraud item ([^"]{20,400}?€[^"]{0,120})"', t)):
    print(m[:230])
