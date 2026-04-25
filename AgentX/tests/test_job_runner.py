from __future__ import annotations

from dataclasses import dataclass

from agentx.core.agent import Plan, PlanStep, ToolResult
from agentx.core.audit import AuditLog
from agentx.jobs.planner import PlannerDecision
from agentx.jobs.runner import JobRunner
from agentx.jobs.storage import JobStore
from agentx.plugins.manager import PluginManager
from agentx.runtime.paths import build_runtime_paths, ensure_runtime_dirs
from agentx.skills.manager import SkillManager
from agentx.tools.base import Tool
from agentx.tools.registry import ToolRegistry
from agentx.config import load_config

from conftest import write_test_config


class ApprovalTool(Tool):
    name = "approval.tool"
    description = "Needs approval"
    requires_confirmation = True


@dataclass
class FakeAgent:
    ctx: object
    tools: ToolRegistry
    executed: int = 0

    def execute(self, plan):
        self.executed += 1
        return [
            ToolResult(
                tool="approval.tool",
                ok=True,
                skipped=False,
                output={"ok": True},
                error=None,
                duration_ms=1.0,
                reason=plan.steps[0].reason,
            )
        ]


def test_job_runner_blocks_for_approval_then_completes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    write_test_config(tmp_path)
    cfg = load_config("config/agentx.toml")
    runtime_paths = build_runtime_paths(cfg)
    ensure_runtime_dirs(runtime_paths)

    class Ctx:
        def __init__(self, cfg, audit):
            self.cfg = cfg
            self.audit = audit

    registry = ToolRegistry()
    registry.register(ApprovalTool())
    audit = AuditLog(cfg.audit.log_path)
    agent = FakeAgent(ctx=Ctx(cfg, audit), tools=registry)
    store = JobStore(cfg=cfg, runtime_paths=runtime_paths)
    runner = JobRunner(
        agent=agent,
        store=store,
        plugin_manager=PluginManager(cfg=cfg, runtime_paths=runtime_paths),
        skill_manager=SkillManager(cfg=cfg, runtime_paths=runtime_paths),
        hint_store=None,
    )

    decision = PlannerDecision(
        status="plan",
        summary="Run approval tool",
        plan=Plan(steps=(PlanStep(tool_name="approval.tool", arguments={}, reason="Need approval"),)),
        raw_text="",
    )
    runner.planner.plan_next = lambda **_: decision  # type: ignore[assignment]
    runner.planner.assess_progress = lambda **_: "complete"  # type: ignore[assignment]

    job = runner.create_job(goal="Run approval-bound tool")
    blocked = runner.run_to_terminal(job.job_id)
    assert blocked.status.value == "blocked"
    assert blocked.pending_approval is not None
    assert agent.executed == 0

    approved = runner.approve_pending(job.job_id, approved=True)
    completed = runner.run_to_terminal(approved.job_id)
    assert completed.status.value == "completed"
    assert agent.executed == 1
