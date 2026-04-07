from bettercopilot.policies.policy_engine import PolicyEngine


def test_policy_assess():
    engine = PolicyEngine()
    bad = "def f():\n    pass    \n"
    res = engine.assess(bad, ['python_style'])
    assert isinstance(res, dict)
    assert 'diagnostics' in res
    assert 'corrected_code' in res
    assert res['corrected_code'].endswith('pass')
