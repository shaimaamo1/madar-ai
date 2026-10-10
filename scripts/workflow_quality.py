"""Inspect the actual exported graphs; never connect to n8n or claim execution."""
import argparse
import json
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSIONS = {'httpRequest': 4.2, 'scheduleTrigger': 1.2, 'executeWorkflowTrigger': 1.1,
            'executeWorkflow': 1.2, 'if': 2.2, 'code': 2, 'webhook': 2,
            'respondToWebhook': 1.4, 'stickyNote': 1, 'manualTrigger': 1, 'errorTrigger': 1}
TRIGGERS = {'scheduleTrigger', 'executeWorkflowTrigger', 'webhook', 'manualTrigger', 'errorTrigger'}


def inspect_graph(flow):
    """Repository schema/reachability checks, distinct from installed n8n validation."""
    errors = []
    nodes = flow.get('nodes', [])
    by_name = {n['name']: n for n in nodes}
    if len(by_name) != len(nodes) or len({n['id'] for n in nodes}) != len(nodes):
        errors.append('Duplicate node name or ID')
    executable = {n['name'] for n in nodes if n['type'] != 'n8n-nodes-base.stickyNote'}
    for n in nodes:
        kind = n['type'].removeprefix('n8n-nodes-base.')
        if not n['type'].startswith('n8n-nodes-base.') or VERSIONS.get(kind) != n.get('typeVersion'):
            errors.append('Node type/version differs from the repository compatibility matrix')
        if len(n.get('position', [])) != 2:
            errors.append('Missing canvas position')
    adjacency = {name: [] for name in executable}
    connections = 0
    for source, outputs in flow.get('connections', {}).items():
        if source not in executable or set(outputs) != {'main'}:
            errors.append('Unsupported source or connection type')
            continue
        for output in outputs['main']:
            for edge in output:
                connections += 1
                target = edge.get('node')
                if target not in executable or edge.get('type') != 'main' or edge.get('index') != 0:
                    errors.append('Unresolved target or unsupported input index')
                else:
                    adjacency[source].append(target)
    for name in executable:
        if by_name[name]['type'] == 'n8n-nodes-base.if':
            ports = flow.get('connections', {}).get(name, {}).get('main', [])
            if len(ports) != 2 or not all(ports):
                errors.append('Condition must expose connected true and false paths')
    entry = [n['name'] for n in nodes if n['type'].removeprefix('n8n-nodes-base.') in TRIGGERS]
    queue, reachable = deque(entry), set()
    while queue:
        name = queue.popleft()
        if name in reachable:
            continue
        reachable.add(name)
        queue.extend(adjacency.get(name, []))
    if not entry or reachable != executable:
        errors.append('Executable node unreachable from an entry point')
    if flow.get('active') is not False:
        errors.append('Export must remain inactive')
    for option in ('saveDataSuccessExecution', 'saveDataErrorExecution'):
        if flow.get('settings', {}).get(option) != 'none':
            errors.append('Workflow must not retain customer execution payloads by default')
    return {'workflow': flow['name'], 'functional_nodes': len(executable), 'connected_nodes': len(reachable),
            'connections': connections, 'repository_validation': 'FAIL' if errors else 'PASS',
            'installed_node_compatibility': 'NOT TESTED', 'live_import': 'NOT TESTED', 'n8n_execution': 'NOT TESTED',
            'error_handling': 'Error Monitor binding applied by the importer; execution NOT TESTED',
            'integration': 'Inactive export; no live provider tests', 'demo_readiness': 'Backend sandbox works; n8n demo execution NOT TESTED',
            'errors': sorted(set(errors))}


def report(folder=ROOT / 'workflows'):
    return {'scope': 'Source graph inspection only. Does not import, activate, execute or connect to n8n.',
            'node_version_basis': 'Pinned repository export matrix; installed n8n still needs execution verification.',
            'workflows': [inspect_graph(json.loads(p.read_text())) for p in sorted(folder.glob('*.json'))]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = report()
    encoded = json.dumps(result, indent=2) + '\n'
    if args.output:
        if args.output.exists():
            parser.error('Use a new output path; existing files are preserved')
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded)
    else:
        print(encoded, end='')
    raise SystemExit(int(any(w['repository_validation'] != 'PASS' for w in result['workflows'])))


if __name__ == '__main__':
    main()
