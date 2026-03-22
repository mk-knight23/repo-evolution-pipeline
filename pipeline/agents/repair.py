"""
Repair Agent — given a generated project and a verification failure report,
ask the LLM for a small set of file edits and apply them.
"""

from __future__ import annotations

import logging
from typing import Any, Literal, TypedDict

from pipeline.core.llm import invoke_with_retry

logger = logging.getLogger("pipeline.repair")


class RepairEdit(TypedDict, total=False):
    action: Literal["create", "update", "delete"]
    file_path: str
    content: str


class RepairPlan(TypedDict, total=False):
    edits: list[RepairEdit]
    notes: str


def apply_repair_plan(files: dict[str, str], plan: dict[str, Any]) -> dict[str, str]:
    """Apply an LLM-proposed repair plan to an in-memory file map."""
    out = dict(files)
    edits = plan.get("edits") or []
    if not isinstance(edits, list):
        return out

    for edit in edits:
        if not isinstance(edit, dict):
            continue
        action = str(edit.get("action", "")).lower()
        file_path = str(edit.get("file_path", "")).strip()
        if not file_path:
            continue

        if action == "delete":
            out.pop(file_path, None)
            continue

        if action in ("create", "update"):
            content = edit.get("content")
            if content is None:
                continue
            out[file_path] = str(content)

    return out


def _summarize_verification_report(verification_report: Any) -> str:
    """
    Accepts either a dict-like object or a VerificationReport model instance.
    """
    try:
        checks = getattr(verification_report, "checks", None) or verification_report.get("checks", [])
    except Exception:
        checks = []

    lines = []
    try:
        report_category = getattr(verification_report, "failure_category", None) or verification_report.get("failure_category", "")
        report_summary = getattr(verification_report, "failure_summary", None) or verification_report.get("failure_summary", "")
        if report_category or report_summary:
            lines.append(f"Failure Category: {report_category or 'unknown'}\nSummary: {report_summary or 'n/a'}")
    except Exception:
        pass

    for c in checks or []:
        try:
            name = getattr(c, "name", None) or c.get("name", "")
            cmd = getattr(c, "command", None) or c.get("command", "")
            success = getattr(c, "success", None)
            if success is None:
                success = c.get("success", False)
            stdout = getattr(c, "stdout", None) or c.get("stdout", "")
            stderr = getattr(c, "stderr", None) or c.get("stderr", "")
            if success:
                continue
            category = getattr(c, "failure_category", None) or c.get("failure_category", "")
            summary = getattr(c, "summary", None) or c.get("summary", "")
            relevant_files = getattr(c, "relevant_files", None) or c.get("relevant_files", [])
            lines.append(
                f"## Failed check: {name}\n"
                f"Category: {category or 'unknown'}\n"
                f"Summary: {summary or 'n/a'}\n"
                f"Relevant files: {', '.join(relevant_files) if relevant_files else 'n/a'}\n"
                f"Command: {cmd}\nSTDERR:\n{str(stderr)[:5000]}\nSTDOUT:\n{str(stdout)[:5000]}"
            )
        except Exception:
            continue
    return "\n\n".join(lines) if lines else "No failed checks were captured."


def _select_repair_context(files: dict[str, str], verification_report: Any = None) -> dict[str, str]:
    """Pick a small set of likely-relevant files for repair prompts."""
    relevant_files: list[str] = []
    failure_category = ""
    try:
        relevant_files = list(
            getattr(verification_report, "relevant_files", None)
            or verification_report.get("relevant_files", [])
        )
        failure_category = str(
            getattr(verification_report, "failure_category", None)
            or verification_report.get("failure_category", "")
        )
    except Exception:
        pass

    key_paths = [
        "package.json",
        "tsconfig.json",
        "app.json",
        "babel.config.js",
        "src/api/client.ts",
        "src/theme/index.ts",
    ]
    if failure_category == "dependencies":
        key_paths.extend(["package-lock.json", "yarn.lock"])
    elif failure_category == "build":
        key_paths.extend(["metro.config.js", "app/_layout.tsx"])

    selected: dict[str, str] = {}

    for p in relevant_files:
        if p in files and p not in selected:
            selected[p] = files[p][:20_000]

    for p in key_paths:
        if p in files:
            selected[p] = files[p][:20_000]

    # Add up to 2 screens for context.
    screens = [p for p in files.keys() if p.startswith("src/screens/") and p.endswith(".tsx")]
    for p in sorted(screens)[:2]:
        selected[p] = files[p][:20_000]

    return selected


async def repair_generated_files(
    files: dict[str, str],
    verification_report: Any,
    *,
    repo_name: str,
) -> dict[str, str]:
    """
    Ask the LLM for a minimal edit plan that fixes verification failures.

    Returns an updated file map (does not mutate input).
    """
    failure_summary = _summarize_verification_report(verification_report)
    ctx = _select_repair_context(files, verification_report)
    ctx_str = "\n\n".join([f"### {p}\n```\n{c}\n```" for p, c in ctx.items()])

    report_category = "unknown"
    report_relevant_files: list[str] = []
    try:
        report_category = str(
            getattr(verification_report, "failure_category", None)
            or verification_report.get("failure_category", "unknown")
        )
        report_relevant_files = list(
            getattr(verification_report, "relevant_files", None)
            or verification_report.get("relevant_files", [])
        )
    except Exception:
        pass

    prompt = f"""You are a senior mobile build engineer.
Fix the generated Expo/React Native project so that local verification passes.

## Repo
- Name: {repo_name}

## Verification Failures
{failure_summary}

## Repair Targeting
- Primary failure category: {report_category}
- Report relevant files: {', '.join(report_relevant_files) if report_relevant_files else 'n/a'}

## Project Context (selected files)
{ctx_str}

## Output (MUST be valid JSON)
Return a JSON object:
{{
  "edits": [
    {{
      "action": "create|update|delete",
      "file_path": "path/relative/to/repo",
      "content": "full file content for create/update (omit for delete)"
    }}
  ],
  "notes": "short explanation"
}}

Constraints:
- Keep changes minimal and targeted to fix the failure.
- Do not introduce secrets.
- Prefer adjusting config/scripts/types over rewriting whole app.
- Prioritize files listed in relevant files before editing unrelated screens.
"""

    plan = await invoke_with_retry(
        prompt=prompt,
        stage="repair",
        heavy=True,
        parse_json=True,
        include_practices=["performance"],
    )
    if not isinstance(plan, dict):
        logger.warning("Repair plan was not a JSON object; skipping repair")
        return dict(files)

    return apply_repair_plan(files, plan)

