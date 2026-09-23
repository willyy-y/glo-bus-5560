"""Extract the GLO-BUS client-side demand model from the JS bundle into model_spec.json."""
import re, json

SRC = open('/tmp/glo-main.js').read()

def get_tables():
    tables = {}
    for m in re.finditer(r'(demand_[a-z_0-9]+):(\[\[.*?\]\])(?=,\w+:|\},)', SRC):
        name = m.group(1)
        if name in tables: continue
        try:
            tables[name] = json.loads(m.group(2))
        except Exception:
            pass
    return tables

def get_constblock():
    i = SRC.find('AN406:1.6')
    start = SRC.rfind('{', 0, i)
    depth=0; end=start
    for k in range(start, min(start+8000, len(SRC))):
        if SRC[k]=='{': depth+=1
        elif SRC[k]=='}':
            depth-=1
            if depth==0: end=k+1; break
    pairs = re.findall(r'([A-Z]{1,3}\d{1,4}):([\d.\-]+)', SRC[start:end])
    return {k: float(v) for k,v in pairs}

def cell_defs():
    """Map each t.Demand.CELL assignment RHS (up to the next ',t.' boundary at depth 0)."""
    defs = {}
    for m in re.finditer(r't\.Demand\.([A-Z]{1,3}\d{1,4})=', SRC):
        cell, s = m.group(1), m.end()
        # scan to comma at paren-depth 0
        depth=0; k=s
        while k < len(SRC):
            c=SRC[k]
            if c=='(': depth+=1
            elif c==')': depth-=1
            elif c==',' and depth==0: break
            k+=1
        defs[cell] = SRC[s:k]
    return defs

def parse_vlookup_cell(rhs):
    """Return dict(table, input_cells, factors) for VLookup-based cells."""
    m = re.search(r'e\.VLookup\((.*?),\s*i\.(demand_[a-z_0-9]+)\)', rhs)
    if not m: return None
    inp, table = m.group(1), m.group(2)
    input_cells = re.findall(r'e\.testVal\("Demand","([A-Z]{1,3}\d{1,4})"\)', inp)
    factors = re.findall(r'e\.testVal\("(Demand|Costs)","([A-Z]{1,3}\d{1,4}|Q\d+)"\)', rhs[m.end():])
    # guard: ===0?0:
    guard = re.findall(r'e\.testVal\("Demand","([A-Z]{1,3}\d{1,4})"\)===0\?0', rhs[:m.start()])
    return {'table': table, 'input_expr': inp[:160], 'input_cells': input_cells,
            'factors': [f[1] for f in factors], 'guard': guard}

def main():
    tables = get_tables()
    consts = get_constblock()
    defs = cell_defs()
    spec = {'tables': tables, 'constants': consts, 'cells': {}}
    for cell, rhs in defs.items():
        p = parse_vlookup_cell(rhs)
        if p:
            spec['cells'][cell] = {'kind': 'vlookup', **p, 'rhs_tail': rhs[-160:]}
        elif 'Math.max(0,e.excelRound(' in rhs:
            ins = re.findall(r'e\.testVal\("Demand","([A-Z]{1,3}\d{1,4})"\)', rhs)
            spec['cells'][cell] = {'kind': 'region_sum', 'inputs': ins}
    json.dump(spec, open('/home/hatch/workspace/glo-bus/engine/model_spec.json','w'), indent=1)
    print("tables:", len(tables), "consts:", len(consts), "vlookup cells:", sum(1 for c in spec['cells'].values() if c['kind']=='vlookup'),
          "region cells:", sum(1 for c in spec['cells'].values() if c['kind']=='region_sum'))
    # show a fully parsed camera additive cell + price + models + image + promo
    for c in ['AA406','AA407','AA415','AA416','AA417','AA419','AA420','AA421','AA423']:
        print(c, '->', json.dumps(spec['cells'].get(c))[:220])

main()
