from bettercopilot.policies.policy_engine import PolicyEngine


def test_policy_bundles():
    pe = PolicyEngine()
    bundles = pe.list_bundles()
    assert 'python' in bundles
    assert isinstance(pe.resolve_bundle('python'), list)
