"""`ai ask` command implementation."""
from bettercopilot.orchestrator.orchestrator import Orchestrator
from bettercopilot.orchestrator.task import Task
from bettercopilot.providers.ollama_local import OllamaLocalProvider
from bettercopilot.mcp.registry import MCPRegistry
from bettercopilot.context.prompt_builder import PromptBuilder
from bettercopilot.context.file_selector import FileSelector
import uuid
import pprint


def run(question: str):
    # Providers map - in real usage this would be configurable
    providers = {"ollama_local": OllamaLocalProvider()}
    registry = MCPRegistry()

    # Build a minimal context and prompt builder
    prompt_builder = PromptBuilder()
    selector = FileSelector('.')
    project_type = None
    try:
        from ...context.project_detector import detect_project_type
        project_type = detect_project_type('.')
    except Exception:
        project_type = None

    selected = selector.select(project_type or 'python')

    orchestrator = Orchestrator(providers, registry, context_builder=prompt_builder)
    task = Task(id=str(uuid.uuid4()), goal=question, provider='ollama_local', files=selected, policies=['python_style'])
    result = orchestrator.run_task(task)

    # Print clean output
    print('\n=== Final Output ===')
    print(result.get('final_text') or '')
    print('\n=== Diffs ===')
    for d in result.get('diffs', []):
        print(d)
    print('\n=== Tool Calls ===')
    pprint.pprint(result.get('tool_calls', []))
    print('\n=== Logs (last) ===')
    if result.get('logs'):
        pprint.pprint(result.get('logs')[-3:])
