"""
PURPOSE: One-shot static HTML export of the dashboard. No server required.
         Useful for browsing offline, attaching to a PR, or committing to
         the repo as a snapshot.

OWNS:
  - Producing /app/output/dashboard.html (path from dashboard.yaml)
  - Embedding the CSS inline so the file is self-contained

HYPERPARAMETERS:
  - All externalized to config/dashboard.yaml + config/rules.yaml
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, os.path.dirname(__file__))

from config_loader import (
    content_src_dir,
    load_dashboard_config,
    load_rules_config,
)
from scanner import scan
from validator import validate
from view_model import bucket_totals, build_tree, filter_summaries, sort_summaries


HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"


def main() -> int:
    dashboard_cfg = load_dashboard_config()
    rules_cfg = load_rules_config()
    content_src = content_src_dir(dashboard_cfg)
    output_html = Path(dashboard_cfg["paths"]["output_html"])

    sresult = scan(content_src, rules_cfg)
    report = validate(sresult, rules_cfg, dashboard_cfg)

    color_buckets = dashboard_cfg["color_buckets"]
    filter_presets = dashboard_cfg["filter_presets"]
    bucket_colors = {b["id"]: b["css_color"] for b in color_buckets}
    enums = rules_cfg.get("enums", {})
    editable_fields = rules_cfg.get("editable_fields", [])
    field_types = rules_cfg.get("field_types", {})
    all_types = sorted({s.type for s in report.summaries.values() if s.type})

    preset, pid = filter_presets[0], filter_presets[0]["id"]
    sortable_columns = dashboard_cfg.get("sortable_columns", [])
    filtered = sort_summaries(filter_summaries(report.summaries, preset, None, None), None, None, sortable_columns)
    tree = build_tree(sresult, report, color_buckets)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

    embed_htmx = bool(dashboard_cfg.get("static_export", {}).get("embed_htmx", False))
    html = env.get_template("base.html.j2").render(
        title=dashboard_cfg["server"]["title"] + " (static)",
        css=css,
        include_htmx=embed_htmx,
        summaries=report.summaries,
        filtered=filtered,
        filter_presets=filter_presets,
        active_preset=pid,
        active_type="",
        all_types=all_types,
        color_buckets=color_buckets,
        bucket_colors=bucket_colors,
        bucket_counts=bucket_totals(report.summaries, [b["id"] for b in color_buckets]),
        enums=enums,
        editable_fields=editable_fields,
        field_types=field_types,
        tree=tree,
        q=None,
        sortable_columns=sortable_columns,
        active_sort="",
        active_sort_dir="",
        issue_count=sum(len(s.issues) for s in report.summaries.values()),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )

    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text(html, encoding="utf-8")
    print(f"wrote {output_html} ({len(html):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
