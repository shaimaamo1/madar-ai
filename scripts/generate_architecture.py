"""Generate presentation SVGs and dashboard diagrams from actual n8n exports."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'docs' / 'diagrams'


def catalog():
    result = []
    for path in sorted((ROOT / 'workflows').glob('*.json')):
        workflow = json.loads(path.read_text())
        nodes = [{'id': n['id'], 'name': n['name'], 'type': n['type'].split('.')[-1], 'position': n['position'],
                  **({'note': n['parameters']['content'], 'width': n['parameters']['width'], 'height': n['parameters']['height']} if n['type'].endswith('.stickyNote') else {})} for n in workflow['nodes']]
        edges = [{'source': name, 'target': link['node'], 'branch': branch} for name, connections in workflow['connections'].items()
                 for branch, links in enumerate(connections.get('main', [])) for link in links]
        result.append({'name': workflow['name'], 'key': path.stem, 'nodes': nodes, 'edges': edges, 'active': workflow['active'],
                       'contracts': [n['parameters']['url'].replace('http://app:8000', '') for n in workflow['nodes'] if 'url' in n['parameters']]})
    return result


def render(flow):
    nodes = flow['nodes']
    width = max(n['position'][0] + n.get('width', 240) for n in nodes) + 80
    height = max(n['position'][1] + n.get('height', 92) for n in nodes) + 170
    shift = 100
    esc = html.escape
    output = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">', f'<title id="title">{esc(flow["name"])} — actual inactive n8n architecture</title>', '<desc id="desc">Generated directly from importable workflow nodes and connections. No workflows are activated.</desc>', '<defs><pattern id="dots" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1" fill="#263b53"/></pattern><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10" fill="#79b2b6"/></marker></defs>', f'<rect width="{width}" height="{height}" fill="#101E31"/><rect width="{width}" height="{height}" fill="url(#dots)"/>', '<g font-family="Segoe UI,Arial,sans-serif">', '<text x="45" y="43" fill="#D8BE83" font-size="13" letter-spacing="3">MADAR AI / AUTOMATION ARCHITECTURE</text>', f'<text x="45" y="82" fill="#F7F2E8" font-size="27" font-weight="600">{esc(flow["name"].removeprefix("MADAR "))}</text>']
    for n in nodes:
        if n['type'] == 'stickyNote':
            x,y=n['position']; y+=shift
            title=n['note'].split('\n')[0].removeprefix('## ')
            output += [f'<rect x="{x}" y="{y}" width="{n["width"]}" height="{n["height"]}" rx="15" fill="#193B572a" stroke="#385b72" stroke-dasharray="6 7"/>', f'<text x="{x+18}" y="{y+25}" fill="#D8BE83" font-size="11" letter-spacing="1.4">{esc(title)}</text>']
    by_name={n['name']:n for n in nodes}
    for e in flow['edges']:
        a,b=by_name[e['source']]['position'],by_name[e['target']]['position']
        x1,y1=a[0]+215,a[1]+shift+42;x2,y2=b[0],b[1]+shift+42
        output.append(f'<path d="M{x1},{y1} C{x1+50},{y1} {x2-55},{y2} {x2},{y2}" fill="none" stroke="#79b2b6" stroke-width="2" marker-end="url(#arrow)"/>')
    for n in nodes:
        if n['type']=='stickyNote':continue
        x,y=n['position'];y+=shift
        kind=n['type']; stroke='#D8BE83' if 'Trigger' in kind or kind=='webhook' else '#3a637c'
        output.append(f'<g data-node-id="{esc(n["id"])}"><rect x="{x}" y="{y}" width="215" height="84" rx="11" fill="#172c43" stroke="{stroke}"/><rect x="{x+13}" y="{y+14}" width="26" height="26" rx="7" fill="#247F8644"/><text x="{x+26}" y="{y+32}" fill="#D8BE83" text-anchor="middle" font-size="12">{"?" if kind=="if" else "↗" if kind=="httpRequest" else "{}" if kind=="code" else "◈"}</text>')
        words=n['name'].split(); lines=['']
        for word in words:
            if len(lines[-1])+len(word)>26:lines.append(word)
            else:lines[-1]+=(' ' if lines[-1] else '')+word
        for i,line in enumerate(lines[:2]):
            output.append(f'<text x="{x+50}" y="{y+27+i*17}" font-size="11" fill="#F7F2E8" font-weight="600">{esc(line)}</text>')
        output.append(f'<text x="{x+15}" y="{y+69}" font-size="10" fill="#adbed2">{esc(kind)}</text></g>')
    count=sum(n['type']!='stickyNote' for n in nodes)
    output += [f'<text x="45" y="{height-36}" font-size="11" fill="#adbed2">{count} executable nodes · source: workflows/{esc(flow["key"])}.json · INACTIVE · live integration NOT VERIFIED</text>', '</g></svg>']
    return '\n'.join(output)+'\n'


def main():
    DEST.mkdir(exist_ok=True)
    flows=catalog()
    for flow in flows:
        (DEST/(flow['key']+'.svg')).write_text(render(flow))
    (ROOT/'frontend/src/workflowCatalog.ts').write_text('// Generated from workflows/*.json by scripts/generate_architecture.py.\nexport const workflowCatalog = '+json.dumps(flows,ensure_ascii=False,indent=2)+';\n')


if __name__=='__main__':
    main()
