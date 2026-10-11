import copy

from scripts.workflow_quality import report, inspect_graph
from scripts.n8n_deploy import workflow_templates


def test_all_real_exports_have_reachable_functional_nodes_and_honest_execution_status():
    rows = report()['workflows']
    assert len(rows) == 14
    from scripts.enterprise_stages import NAMES
    majors = [r for r in rows if r['workflow'] in NAMES.values()]
    assert len(majors) == 8
    assert all(r['functional_nodes'] >= 30 for r in majors)
    for row in rows:
        assert row['repository_validation'] == 'PASS', row['errors']
        assert row['functional_nodes'] == row['connected_nodes']
        assert row['n8n_execution'] == row['live_import'] == row['installed_node_compatibility'] == 'NOT TESTED'


def test_quality_report_rejects_disconnected_nodes_bad_versions_and_dangling_edges():
    source = next(f for f in workflow_templates() if f['name'] == 'MADAR Omnichannel Intake')
    for defect in ('disconnected', 'version', 'edge', 'branch', 'activation', 'payload-retention'):
        flow = copy.deepcopy(source)
        if defect == 'disconnected':
            node = copy.deepcopy(flow['nodes'][1])
            node.update(id='unreachable', name='Unreachable')
            flow['nodes'].append(node)
        elif defect == 'version':
            flow['nodes'][0]['typeVersion'] = 999
        elif defect == 'edge':
            flow['connections']['Authenticated normalized events']['main'][0][0]['node'] = 'Missing target'
        elif defect == 'branch':
            branch = next(n['name'] for n in flow['nodes'] if n['type'].endswith('.if'))
            flow['connections'][branch]['main'][1] = []
        elif defect == 'activation':
            flow['active'] = True
        else:
            flow['settings']['saveDataSuccessExecution'] = 'all'
        assert inspect_graph(flow)['repository_validation'] == 'FAIL', defect
