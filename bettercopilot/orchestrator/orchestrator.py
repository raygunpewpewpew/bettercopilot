"""Headless orchestrator that runs tasks using providers, MCP tools, and policies.

This orchestrator implements a richer meta-critic loop:
  - message building (system, context, previous iterations, user goal)
  - generator call (provider)
  - optional tool calls routed via MCP
  - critic evaluation
  - policy assessment & auto-fix
  - refinement / retry

The result is a structured dict containing final text, diffs, logs, tool_calls
and critic feedback.
"""
from typing import Dict, Any, List, Optional
from difflib import unified_diff
import logging
import time

from ..policies.policy_engine import PolicyEngine
from ..meta_critic.generator import Generator
from ..meta_critic.critic import Critic
from ..meta_critic.refinement import RefinementEngine
from .tool_router import ToolRouter
from ..context.context import Context
from ..logging import init_run, log_event, write_summary


class Orchestrator:
    def __init__(self, providers: Dict[str, Any], mcp_registry, context_builder=None):
        self.logger = logging.getLogger("Orchestrator")
        self.providers = providers
        self.mcp_registry = mcp_registry
        self.tool_router = ToolRouter(mcp_registry)
        self.context_builder = context_builder
        self.policy_engine = PolicyEngine()

    def _build_messages(self, goal: str, context_obj: Optional[Context], previous_iterations: List[Dict]) -> List[Dict[str, str]]:
        messages: List[Dict[str, str]] = []

        # System prompt (include policy summary)
        system_parts = ["You are BetterCopilot, a code + ROM assistant."]
        if context_obj and context_obj.policy_summaries:
            system_parts.append("Policies: " + ", ".join(p['name'] for p in context_obj.policy_summaries))
        messages.append({"role": "system", "content": "\n".join(system_parts)})

        # Context prompt with project metadata and selected files
        if context_obj:
            ctx_lines = [f"Project type: {context_obj.project_type}"]
            if context_obj.selected_files:
                ctx_lines.append(f"Selected files: {', '.join(context_obj.selected_files[:10])}")
            messages.append({"role": "system", "content": "\n".join(ctx_lines)})

        # Previous iterations inserted as assistant messages (helps provide continuity)
        for it in previous_iterations:
            messages.append({"role": it.get('role', 'assistant'), "content": it.get('content', '')})

        # User goal
        messages.append({"role": "user", "content": goal})
        return messages

    def run_task(self, task, max_retries: int = 3) -> Dict[str, Any]:
        provider_name = task.provider or next(iter(self.providers.keys()))
        provider = self.providers.get(provider_name)
        gen = Generator(provider)
        critic = Critic(self.policy_engine)
        refine = RefinementEngine(self.policy_engine)

        # Build context object if possible
        context_obj: Optional[Context] = None
        try:
            if self.context_builder:
                # context_builder may be a PromptBuilder; allow context module to be used
                from ..context.file_selector import FileSelector
                from ..context.project_detector import detect_project_type

                project_type = detect_project_type('.')
                selector = FileSelector('.')
                selected = selector.select(project_type or 'python')
                # Tool schemas from registry (discover at runtime)
                try:
                    discovered = {}
                    if hasattr(self.mcp_registry, 'discover_tools'):
                        discovered = self.mcp_registry.discover_tools()
                    else:
                        # fallback
                        discovered = {t: {"schema": {}} for t in self.mcp_registry.list_tools()}
                    tool_schemas = [v.get('schema') if isinstance(v, dict) else {} for k, v in discovered.items()]
                except Exception:
                    tool_schemas = []
                policy_summaries = [{"name": p} for p in self.policy_engine.list_policies()]
                from ..context.context import Context as Ctx
                context_obj = Ctx(root='.', project_type=project_type or 'unknown', selected_files=selected, tool_schemas=tool_schemas, policy_summaries=policy_summaries)
        except Exception:
            self.logger.exception("Failed to build context")

        previous_iterations: List[Dict[str, str]] = []
        logs: List[Dict[str, Any]] = []
        diffs: List[str] = []
        tool_calls_executed: List[Dict[str, Any]] = []
        critic_feedback: List[Dict[str, Any]] = []
        final_output: Optional[str] = None

        # Initialize run logging
        run_id = init_run({"task_id": task.id, "goal": task.goal, "provider": provider_name})
        log_event(run_id, {"level": "info", "type": "task_start", "task": task.id})

        attempt = 0
        while attempt < max_retries:
            attempt += 1
            messages = self._build_messages(task.goal, context_obj, previous_iterations)

            self.logger.info("[provider_call] provider=%s attempt=%d", provider_name, attempt)
            start_t = time.time()
            try:
                out = gen.generate(messages, tools=task.tools)
            except Exception as e:
                self.logger.exception("Provider generate failed: %s", e)
                logs.append({"attempt": attempt, "provider_error": str(e)})
                log_event(run_id, {"level": "error", "type": "provider_error", "attempt": attempt, "error": str(e)})
                continue
            elapsed = time.time() - start_t
            logs.append({"attempt": attempt, "provider": provider_name, "elapsed": elapsed, "output_preview": (out.get('text') or '')[:400]})
            log_event(run_id, {"level": "info", "type": "provider_call", "provider": provider_name, "elapsed": elapsed, "preview": (out.get('text') or '')[:400]})

            # Route tool calls if present
            for tc in out.get('tool_calls', []) or []:
                try:
                    self.logger.info("[tool_call] routing tool=%s", tc.get('tool'))
                    resp = self.tool_router.route_call(tc)
                    tool_calls_executed.append(resp)
                    # Insert tool response into previous iterations to inform next generation
                    previous_iterations.append({"role": "assistant", "content": resp.get('response_text', str(resp.get('response', '')))})
                    logs.append({"attempt": attempt, "tool_call": tc, "tool_response": resp})
                    log_event(run_id, {"level": "info", "type": "tool_call", "tool": tc.get('tool'), "resp": resp})
                except Exception as e:
                    self.logger.exception("Tool call failed: %s", e)
                    logs.append({"attempt": attempt, "tool_call_error": str(e), "tool_call": tc})
                    log_event(run_id, {"level": "error", "type": "tool_call_error", "tool": tc.get('tool'), "error": str(e)})

            # Critic evaluation
            eval_res = critic.evaluate(out, task.policies or self.policy_engine.list_policies())
            logs.append({"attempt": attempt, "critic_evaluation": eval_res})
            critic_feedback.append(eval_res)
            log_event(run_id, {"level": "info", "type": "critic_evaluation", "attempt": attempt, "evaluation": eval_res})

            # Policy assessment & auto-fix
            assessment = self.policy_engine.assess(out.get('text', ''), task.policies or self.policy_engine.list_policies())
            logs.append({"attempt": attempt, "policy_assessment": assessment})
            log_event(run_id, {"level": "info", "type": "policy_assessment", "attempt": attempt, "assessment": assessment})

            if assessment.get('corrected_code') and assessment.get('corrected_code') != out.get('text', ''):
                old = out.get('text', '').splitlines(keepends=True)
                new = assessment.get('corrected_code', '').splitlines(keepends=True)
                diff = ''.join(unified_diff(old, new, lineterm=''))
                diffs.append(diff)
                logs.append({"attempt": attempt, "policy_correction_diff": diff})
                log_event(run_id, {"level": "info", "type": "policy_correction_diff", "attempt": attempt, "diff": diff})

            # Decide whether acceptable
            if assessment.get('acceptable'):
                final_output = assessment.get('corrected_code') or out.get('text')
                logs.append({"attempt": attempt, "result": "accepted"})
                log_event(run_id, {"level": "info", "type": "accepted", "attempt": attempt})
                break

            # Refinement step: try to auto-fix or request retry
            refinement = refine.refine(out, eval_res.get('diagnostics', []))
            logs.append({"attempt": attempt, "refinement": refinement})
            log_event(run_id, {"level": "info", "type": "refinement", "attempt": attempt, "refinement": refinement})

            if refinement.get('changed'):
                final_output = refinement.get('fixed_text')
                logs.append({"attempt": attempt, "result": "fixed_and_accepted"})
                diffs.append(Context.compute_diffs(out.get('text', ''), final_output))
                log_event(run_id, {"level": "info", "type": "fixed_output", "attempt": attempt})
                break

            # Prepare a brief assistant message describing the critic feedback for retry
            previous_iterations.append({"role": "assistant", "content": f"Critic feedback: {eval_res.get('diagnostics', [])[:3]}"})

        result = {
            "task_id": task.id,
            "final_text": final_output,
            "diffs": diffs,
            "logs": logs,
            "tool_calls": tool_calls_executed,
            "critic_feedback": critic_feedback,
        }
        write_summary(run_id, result)
        return result
