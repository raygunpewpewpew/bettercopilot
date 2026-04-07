"""`ai fix` command implementation."""
from bettercopilot.policies.policy_engine import PolicyEngine
import pprint


def run(path: str):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"File not found: {path}")
        return

    engine = PolicyEngine()
    assessment = engine.assess(code, engine.list_policies())
    print('\n=== Diagnostics ===')
    pprint.pprint(assessment.get('diagnostics', []))
    print('\n=== Corrected Preview ===')
    print((assessment.get('corrected_code') or '')[:800])
    print('\n=== Acceptable: %s' % assessment.get('acceptable'))
