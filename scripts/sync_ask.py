#!/usr/bin/env python3
"""Synchronous test: build an orchestrator and run a single ask synchronously.

Prints the orchestrator result to stdout for quick verification.
"""
import sys
from pathlib import Path
root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(root))

from bettercopilot.ui.gui.api import _make_orchestrator
from bettercopilot.orchestrator.task import Task
import uuid

orch = _make_orchestrator()
print('Orchestrator providers:', list(orch.providers.keys()))

t = Task(id=str(uuid.uuid4()), goal='Hello from synchronous test. Say a short greeting.')
res = orch.run_task(t)
print('\n--- SYNC RESULT ---')
print(res)
