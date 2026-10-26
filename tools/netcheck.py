"""Export a KiCad netlist and print nets as name: REF.pin(pinname) ..."""
import subprocess, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from schgen import parse, find, find1, uq
KCLI = os.environ.get('KICAD_CLI', os.path.expanduser('~/.backplane-bend/kicad/10.99.0-bp.4/bin/kicad-cli'))

def nets(sch):
    out = sch.replace(".kicad_sch", ".net")
    subprocess.run([KCLI, "sch", "export", "netlist", "--format", "kicadsexpr", "-o", out, sch],
                   check=True, capture_output=True)
    tree = parse(open(out).read())
    res = {}
    for n in find(find1(tree, "nets"), "net"):
        name = uq(find1(n, "name")[1])
        nodes = []
        for nd in find(n, "node"):
            pf = find1(nd, "pinfunction")
            nodes.append(uq(find1(nd, "ref")[1]) + "." + uq(find1(nd, "pin")[1]) + (f"({uq(pf[1])})" if pf else ""))
        res[name] = nodes
    return res

if __name__ == "__main__":
    for k, v in sorted(nets(sys.argv[1]).items()):
        print(f"{k}: {' '.join(v)}")
