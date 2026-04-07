from bettercopilot.meta_critic.critic import Critic
from bettercopilot.policies.policy_engine import PolicyEngine


def test_critic_scores():
    pe = PolicyEngine()
    critic = Critic(pe)
    output = {"text": "print('hello')", "tool_calls": []}
    res = critic.evaluate(output, ['python_style'])
    assert 'score' in res
    assert 'categories' in res
    assert isinstance(res['categories']['clarity'], float)
