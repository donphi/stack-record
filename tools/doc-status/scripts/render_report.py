"""
PURPOSE: One-shot Markdown report export. Sections defined declaratively in
         dashboard.yaml.report_sections. Commit-friendly diff every run.

OWNS:
  - Producing /app/output/report.md (path from dashboard.yaml)
  - Section iteration driven by config; no section names in code
  - Summary header counts per bucket

HYPERPARAMETERS:
  - All externalized to config/dashboard.yaml + config/rules.yaml
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, os.path.dirname(__file__))

from config_loader import (
    content_src_dir,
    load_dashboard_config,
    load_rules_config,
)
from scanner import scan
from validator import NoteSummary, validate
from view_model import bucket_totals, filter_summaries


def _row(s: NoteSummary) -> str:
    overdue = f"+{s.days_overdue}d" if s.days_overdue else ""
    return (
        f"| `{s.slug or '/'}` | {s.title} | {s.type} | {s.status or ''} | "
        f"{s.review_cycle or ''} | {s.last_reviewed or ''} | {overdue} | "
        f"{s.closure_score if s.closure_score is not None else ''} | "
        f"{s.closure_status or ''} | {s.open_questions_count} | {len(s.issues)} |"
    )


HEADER = (
    "| Slug | Title | Type | Status | Cycle | Last reviewed | Overdue | "
    "Closure | Closed? | Open Q | Issues |"
)
SEP = "|" + "|".join(["---"] * 11) + "|"


def main() -> int:
    dashboard_cfg = load_dashboard_config()
    rules_cfg = load_rules_config()
    content_src = content_src_dir(dashboard_cfg)
    output_md = Path(dashboard_cfg["paths"]["output_md"])

    sresult = scan(content_src, rules_cfg)
    report = validate(sresult, rules_cfg, dashboard_cfg)

    color_buckets = dashboard_cfg["color_buckets"]
    bucket_ids = [b["id"] for b in color_buckets]
    counts = bucket_totals(report.summaries, bucket_ids)

    lines: list[str] = []
    lines.append("# doc-status report")
    lines.append("")
    lines.append(f"_Generated: {datetime.now(timezone.utc).isoformat(timespec='seconds')}_")
    lines.append("")
    lines.append(f"**Total notes:** {len(report.summaries)}  ·  **Total issues:** {sum(len(s.issues) for s in report.summaries.values())}")
    lines.append("")
    lines.append("| Bucket | Count |")
    lines.append("|---|---:|")
    for b in color_buckets:
        lines.append(f"| {b['label']} | {counts.get(b['id'], 0)} |")
    lines.append("")

    sections = dashboard_cfg.get("report_sections", [])
    for section in sections:
        sid = section["id"]
        title = section["title"]
        if sid == "summary":
            continue
        flt = section.get("filter", {})
        preset_like: dict[str, Any] = {"where": flt}
        rows = filter_summaries(report.summaries, preset_like, None, None)
        lines.append(f"## {title}")
        lines.append("")
        lines.append(f"_{len(rows)} note{'s' if len(rows) != 1 else ''}._")
        lines.append("")
        if not rows:
            lines.append("None.")
            lines.append("")
            continue
        lines.append(HEADER)
        lines.append(SEP)
        for s in rows:
            lines.append(_row(s))
        lines.append("")

    lines.append("## All issues")
    lines.append("")
    if not report.issues:
        lines.append("None.")
    else:
        lines.append("| Severity | Slug | Field | Type | Message |")
        lines.append("|---|---|---|---|---|")
        for issue in sorted(report.issues, key=lambda i: (i.severity, i.note_slug)):
            msg = issue.message.replace("|", "\\|")
            lines.append(f"| {issue.severity} | `{issue.note_slug or '/'}` | `{issue.field_name}` | `{issue.issue_type}` | {msg} |")
    lines.append("")

    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {output_md} ({len('\n'.join(lines)):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
