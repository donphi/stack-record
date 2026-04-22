"""
PURPOSE: FastAPI app for the live, editable doc-status dashboard.
         Serves the colored tree + filterable tables + inline editing.

OWNS:
  - Routes: GET /, GET /api/table, PATCH /api/notes/{slug}/field
  - In-memory cache of the latest ScanResult + ValidationReport
  - Filesystem watcher (watchfiles) that invalidates the cache on any
    change under content_src
  - Coordinating scanner + validator + writer (no business logic here)

HYPERPARAMETERS:
  - All externalized to config/dashboard.yaml + config/rules.yaml
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader, select_autoescape

sys.path.insert(0, os.path.dirname(__file__))

from config_loader import (
    content_src_dir,
    load_dashboard_config,
    load_rules_config,
)
from scanner import ScanResult, scan
from validator import ValidationReport, validate
from view_model import bucket_totals, build_tree, filter_summaries, next_sort_direction, sort_summaries
from writer import WriterError, write_field


HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR = HERE / "static"


class AppState:
    def __init__(self) -> None:
        self.dashboard_cfg: dict[str, Any] = load_dashboard_config()
        self.rules_cfg: dict[str, Any] = load_rules_config()
        self.content_src: Path = content_src_dir(self.dashboard_cfg)
        self.scan: ScanResult | None = None
        self.report: ValidationReport | None = None
        self._lock = asyncio.Lock()
        self._css: str = (STATIC_DIR / "styles.css").read_text(encoding="utf-8")

        self._jinja = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def refresh(self) -> None:
        self.scan = scan(self.content_src, self.rules_cfg)
        self.report = validate(self.scan, self.rules_cfg, self.dashboard_cfg)

    async def refresh_locked(self) -> None:
        async with self._lock:
            self.refresh()

    def render(self, template: str, **ctx: Any) -> str:
        return self._jinja.get_template(template).render(**ctx)


state = AppState()
state.refresh()

app = FastAPI(title=state.dashboard_cfg.get("server", {}).get("title", "doc-status"))
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _common_context(filtered: list[Any], q: str | None, preset_id: str, type_filter: str | None, sort_id: str | None, sort_dir: str | None) -> dict[str, Any]:
    assert state.scan is not None and state.report is not None
    color_buckets = state.dashboard_cfg["color_buckets"]
    filter_presets = state.dashboard_cfg["filter_presets"]
    sortable_columns = state.dashboard_cfg.get("sortable_columns", [])
    bucket_colors = {b["id"]: b["css_color"] for b in color_buckets}
    tree = build_tree(state.scan, state.report, color_buckets)
    enums = state.rules_cfg.get("enums", {})
    editable_fields = state.rules_cfg.get("editable_fields", [])
    field_types = state.rules_cfg.get("field_types", {})
    all_types = sorted({s.type for s in state.report.summaries.values() if s.type})
    active_sort_dir = sort_dir
    if sort_id and not sort_dir:
        cfg = next((c for c in sortable_columns if c["id"] == sort_id), None)
        if cfg:
            active_sort_dir = cfg.get("default_direction", "desc")
    return {
        "title": state.dashboard_cfg["server"]["title"],
        "css": state._css,
        "include_htmx": True,
        "summaries": state.report.summaries,
        "filtered": filtered,
        "filter_presets": filter_presets,
        "active_preset": preset_id,
        "active_type": type_filter or "",
        "all_types": all_types,
        "color_buckets": color_buckets,
        "bucket_colors": bucket_colors,
        "bucket_counts": bucket_totals(state.report.summaries, [b["id"] for b in color_buckets]),
        "enums": enums,
        "editable_fields": editable_fields,
        "field_types": field_types,
        "tree": tree,
        "q": q,
        "sortable_columns": sortable_columns,
        "active_sort": sort_id or "",
        "active_sort_dir": active_sort_dir or "",
        "next_sort_direction": next_sort_direction,
        "issue_count": sum(len(s.issues) for s in state.report.summaries.values()),
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def _resolve_preset(preset_id: str | None) -> tuple[dict[str, Any], str]:
    presets = state.dashboard_cfg["filter_presets"]
    if preset_id:
        for p in presets:
            if p["id"] == preset_id:
                return p, preset_id
    return presets[0], presets[0]["id"]


def _filtered_and_sorted(p: dict[str, Any], q: str | None, type_filter: str | None, sort_id: str | None, sort_dir: str | None) -> list[Any]:
    filtered = filter_summaries(state.report.summaries, p, q, type_filter)
    sortable_columns = state.dashboard_cfg.get("sortable_columns", [])
    return sort_summaries(filtered, sort_id, sort_dir, sortable_columns)


@app.get("/", response_class=HTMLResponse)
async def index(preset: str | None = None, q: str | None = None, type: str | None = None, sort: str | None = None, dir: str | None = None, refresh: str | None = None) -> HTMLResponse:
    if state.report is None or refresh:
        await state.refresh_locked()
    p, pid = _resolve_preset(preset)
    filtered = _filtered_and_sorted(p, q, type, sort, dir)
    ctx = _common_context(filtered, q, pid, type, sort, dir)
    return HTMLResponse(state.render("base.html.j2", **ctx))


@app.get("/api/table", response_class=HTMLResponse)
async def api_table(preset: str | None = None, q: str | None = None, type: str | None = None, sort: str | None = None, dir: str | None = None) -> HTMLResponse:
    if state.report is None:
        await state.refresh_locked()
    p, pid = _resolve_preset(preset)
    filtered = _filtered_and_sorted(p, q, type, sort, dir)
    ctx = _common_context(filtered, q, pid, type, sort, dir)
    return HTMLResponse(state.render("notes_table.html.j2", **ctx))


@app.get("/api/refresh", response_class=HTMLResponse)
async def api_refresh() -> HTMLResponse:
    await state.refresh_locked()
    return HTMLResponse("<p>refreshed</p>")


@app.patch("/api/notes/{slug:path}/field", response_class=HTMLResponse)
async def patch_field(slug: str, request: Request, field: str = Form(...), value: str = Form(...)) -> HTMLResponse:
    if state.report is None or state.scan is None:
        await state.refresh_locked()
    note = state.scan.notes.get(slug)
    if note is None:
        raise HTTPException(status_code=404, detail=f"unknown slug: {slug}")
    parsed_value: Any = value
    field_type = state.rules_cfg.get("field_types", {}).get(field)
    if field_type == "integer":
        try:
            parsed_value = int(value)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"{field}: '{value}' is not an integer")
    elif field_type == "string_list":
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                parsed_value = parsed
        except (ValueError, json.JSONDecodeError):
            parsed_value = value
    try:
        write_field(note.abs_meta_path, field, parsed_value, state.rules_cfg)
    except WriterError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    await state.refresh_locked()
    summary = state.report.summaries[slug]
    ctx = _common_context([summary], None, "all", None, None, None)
    ctx["s"] = summary
    return HTMLResponse(state.render("note_row.html.j2", **ctx))


@app.on_event("startup")
async def _startup() -> None:
    if not state.dashboard_cfg.get("server", {}).get("watch_filesystem"):
        return
    asyncio.create_task(_watch_loop())


async def _watch_loop() -> None:
    try:
        from watchfiles import awatch
    except Exception:
        return
    debounce_ms = int(state.dashboard_cfg["server"].get("watch_debounce_ms", 300))
    async for _changes in awatch(str(state.content_src), step=debounce_ms):
        try:
            await state.refresh_locked()
        except Exception as exc:
            print(f"[watcher] refresh failed: {exc}", file=sys.stderr)
