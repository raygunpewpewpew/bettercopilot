from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.orchestrator.task import Task
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry


def test_orchestrator_run():
    providers = {'ollama_local': OllamaLocalProvider()}
    registry = MCPRegistry()
    orch = Orchestrator(providers, registry)
    task = Task(id='t1', goal='Write hello world in Python', provider='ollama_local', policies=['python_style'])
    res = orch.run_task(task)
    assert res.get('task_id') == 't1'
    assert 'final_text' in res
    assert 'logs' in res
    assert 'critic_feedback' in res
