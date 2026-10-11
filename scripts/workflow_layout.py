"""Deterministic left-to-right layout of actual n8n nodes; no canvas decorations."""
from collections import defaultdict


def arrange(nodes, connections):
    nodes = [n for n in nodes if n['type'] != 'n8n-nodes-base.stickyNote']
    by_name = {n['name']: n for n in nodes}
    incoming = defaultdict(list)
    for source, outputs in connections.items():
        for port, edges in enumerate(outputs['main']):
            for edge in edges:
                incoming[edge['node']].append((source, port))
    remaining = set(by_name)
    depth, branch = {}, {}
    while remaining:
        ready = sorted(name for name in remaining
                       if all(source in depth for source, _ in incoming[name]))
        if not ready:
            raise ValueError('Layout requires a connected acyclic workflow graph')
        for name in ready:
            parents = incoming[name]
            depth[name] = max((depth[source] + 1 for source, _ in parents), default=0)
            branch[name] = min((branch[source] + int(port != 0) for source, port in parents), default=0)
            remaining.remove(name)
    layers = defaultdict(list)
    for name in by_name:
        layers[depth[name]].append(name)
    for column, names in layers.items():
        occupied = set()
        for name in sorted(names, key=lambda name: (branch[name], name)):
            lane = branch[name]
            while lane in occupied:
                lane += 1
            occupied.add(lane)
            by_name[name]['position'] = [160 + column * 320, 220 + lane * 260]
    return nodes
