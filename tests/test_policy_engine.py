from bettercopilot.policies.policy_engine import PolicyEngine


def test_policy_engine_basic():
    engine = PolicyEngine()
    code = "def f():\n    pass\n"  # proper code, no trailing whitespace
    diags = engine.run(['python_style'], code)
    assert isinstance(diags, list)

    bad = "def f():\n    pass    \n"  # trailing whitespace
    diags2 = engine.run(['python_style'], bad)
    assert any(d.get('message') == 'Trailing whitespace' for d in diags2)
