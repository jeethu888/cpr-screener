import json, glob

files = glob.glob('cpr_data*.json')
for fname in files:
    with open(fname, 'r', encoding='utf-8') as f:
        data = json.load(f)
    changed = 0
    for r in data['results']:
        pivot = r.get('pivot', 0)
        bc = r.get('bc', 0)
        lc = r.get('close', 0)
        if lc > 0:
            new_narrow = bool(abs(pivot - bc) < (lc * 0.001))
            if new_narrow != r.get('narrow_cpr'):
                sym = r['symbol']
                diff = abs(pivot - bc)
                thresh = lc * 0.001
                print(f"{fname}: {sym}  |pivot-bc|={diff:.3f} < {thresh:.3f}  => {r['narrow_cpr']} -> {new_narrow}")
                r['narrow_cpr'] = new_narrow
                changed += 1
    if changed:
        with open(fname, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        print(f"  Saved {fname} ({changed} stocks updated)\n")
    else:
        print(f"{fname}: no changes needed")
