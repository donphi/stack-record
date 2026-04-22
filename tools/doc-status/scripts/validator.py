"""
PURPOSE: Generic, config-driven rule engine. Reads rules.yaml + a ScanResult,
         produces a list of Issue records and a per-note summary used by the
         dashboard, the static export, and the markdown report.

OWNS:
  - Required-key validation (global + per-type)
  - Enum validation (status, closure_status, review_cycle, decision_status)
  - ID-pattern validation (regex from rules.yaml.note_types[T].id_pattern)
  - Date format + closure_score range validation
  - Staleness (last_reviewed vs review_cycle window)
  - Heading conformity vs the per-type _template/example.mdx.template
  - Tag prefix + character format

HYPERPARAMETERS:
  - All externalized to config/rules.yaml — zero hardcoded values here
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Iterable

from scanner import Note, ScanResult


SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
SEVERITY_INFO = "info"


@dataclass
class Issue:
    severity: str
    note_slug: str
    field_name: str
    issue_type: str
    message: str


@dataclass
class NoteSummary:
    slug: str
    title: str
    type: str
    status: str | None
    closure_score: int | None
    closure_status: str | None
    review_cycle: str | None
    last_reviewed: str | None
    days_since_review: int | None
    days_overdue: int | None
    open_questions_count: int
    issues: list[Issue] = field(default_factory=list)
    flags: dict[str, bool] = field(default_factory=dict)
    bucket_id: str = "blue"
    bucket_label: str = "Active"
    bucket_color: str = "#0366d6"


@dataclass
class ValidationReport:
    summaries: dict[str, NoteSummary] = field(default_factory=dict)
    issues: list[Issue] = field(default_factory=list)


def _parse_date(value: Any, fmt: str) -> date | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), fmt).date()
    except ValueError:
        return None


def _flatten_issue_types(issues: Iterable[Issue]) -> set[str]:
    return {i.issue_type for i in issues}


def _bucket_for(flags: dict[str, bool], buckets: list[dict[str, Any]]) -> dict[str, Any]:
    for b in buckets:
        when_any = b.get("when_any") or []
        if not when_any:
            return b
        if any(flags.get(name) for name in when_any):
            return b
    return buckets[-1]


def validate(scan: ScanResult, rules_cfg: dict[str, Any], dashboard_cfg: dict[str, Any], today: date | None = None) -> ValidationReport:
    if today is None:
        today = date.today()

    mandatory_keys = rules_cfg.get("mandatory_meta_keys")
    if not isinstance(mandatory_keys, list):
        raise KeyError("rules.yaml: mandatory_meta_keys (list) is required")

    type_specific = rules_cfg.get("type_specific_mandatory_keys") or {}
    enums = rules_cfg.get("enums") or {}
    note_types_cfg = rules_cfg.get("note_types") or {}
    closure_range = rules_cfg.get("closure_score_range")
    if not (isinstance(closure_range, list) and len(closure_range) == 2):
        raise KeyError("rules.yaml: closure_score_range [min, max] is required")
    date_format = rules_cfg.get("date_format")
    if not isinstance(date_format, str):
        raise KeyError("rules.yaml: date_format is required")
    date_fields = rules_cfg.get("date_fields") or []
    staleness_days = rules_cfg.get("staleness_days") or {}
    overdue_mult = rules_cfg.get("overdue_multipliers") or {}
    if "warning" not in overdue_mult or "error" not in overdue_mult:
        raise KeyError("rules.yaml: overdue_multipliers.warning + .error required")
    heading_check = rules_cfg.get("heading_check") or {}
    tag_format_cfg = rules_cfg.get("tag_format") or {}
    low_closure_threshold = dashboard_cfg.get("low_closure_threshold")
    if low_closure_threshold is None:
        raise KeyError("dashboard.yaml: low_closure_threshold is required")
    color_buckets = dashboard_cfg.get("color_buckets") or []
    if not color_buckets:
        raise KeyError("dashboard.yaml: color_buckets is required")

    report = ValidationReport()

    for slug, note in sorted(scan.notes.items()):
        meta = note.meta
        issues: list[Issue] = []

        if "_parse_error" in meta:
            issues.append(Issue(SEVERITY_ERROR, slug, "<file>", "json_parse_error", f"index.meta.json failed to parse: {meta['_parse_error']}"))

        # Mandatory keys
        for key in mandatory_keys:
            if key not in meta:
                issues.append(Issue(SEVERITY_ERROR, slug, key, "missing_mandatory", f"missing required key '{key}'"))

        # Type
        type_name = meta.get("type")
        if type_name and type_name not in note_types_cfg:
            issues.append(Issue(SEVERITY_ERROR, slug, "type", "invalid_type", f"unknown type '{type_name}' (not in rules.yaml note_types)"))

        # Type-specific mandatory keys
        if isinstance(type_name, str):
            for extra in type_specific.get(type_name, []):
                if extra not in meta:
                    issues.append(Issue(SEVERITY_ERROR, slug, extra, "missing_mandatory", f"type '{type_name}' requires key '{extra}'"))

        # ID pattern
        note_id = meta.get("id")
        if isinstance(type_name, str) and type_name in note_types_cfg and isinstance(note_id, str):
            pattern = note_types_cfg[type_name].get("id_pattern")
            if pattern and not re.match(pattern, note_id):
                issues.append(Issue(SEVERITY_ERROR, slug, "id", "invalid_id", f"id '{note_id}' does not match pattern {pattern}"))

        # Enum values
        for enum_field, allowed in enums.items():
            if enum_field in meta and meta[enum_field] is not None:
                value = meta[enum_field]
                if value not in allowed:
                    issues.append(Issue(SEVERITY_ERROR, slug, enum_field, "invalid_enum", f"'{enum_field}' value '{value}' not in {sorted(allowed)}"))

        # Closure score range
        cs = meta.get("closure_score")
        if isinstance(cs, int):
            cmin, cmax = closure_range
            if cs < cmin or cs > cmax:
                issues.append(Issue(SEVERITY_ERROR, slug, "closure_score", "invalid_range", f"closure_score {cs} outside [{cmin}, {cmax}]"))
        elif "closure_score" in meta and cs is not None:
            issues.append(Issue(SEVERITY_ERROR, slug, "closure_score", "invalid_type", "closure_score must be an integer"))

        # Date format
        for df in date_fields:
            if df in meta:
                v = meta[df]
                if isinstance(v, str) and v.strip() and _parse_date(v, date_format) is None:
                    issues.append(Issue(SEVERITY_ERROR, slug, df, "invalid_date", f"'{df}' value '{v}' does not match format {date_format}"))

        # Staleness
        review_cycle = meta.get("review_cycle")
        last_reviewed_raw = meta.get("last_reviewed")
        last_reviewed_dt = _parse_date(last_reviewed_raw, date_format) if isinstance(last_reviewed_raw, str) else None
        days_since: int | None = None
        days_overdue: int | None = None
        if last_reviewed_dt is not None:
            days_since = (today - last_reviewed_dt).days
        if isinstance(review_cycle, str) and review_cycle in staleness_days and last_reviewed_dt is not None:
            window = staleness_days[review_cycle]
            overdue = days_since - window if days_since is not None else 0
            if overdue > 0:
                days_overdue = overdue
                if overdue >= int(window * overdue_mult["error"]):
                    issues.append(Issue(SEVERITY_ERROR, slug, "last_reviewed", "overdue_error", f"overdue by {overdue} days (cycle={review_cycle}, window={window})"))
                elif overdue > int(window * overdue_mult["warning"]) - window:
                    issues.append(Issue(SEVERITY_WARNING, slug, "last_reviewed", "overdue_warning", f"overdue by {overdue} days (cycle={review_cycle}, window={window})"))

        # Heading conformity
        if heading_check.get("enabled") and isinstance(type_name, str) and type_name in scan.templates:
            tpl_headings = scan.templates[type_name].headings
            actual_headings = note.headings
            cs_flag = bool(heading_check.get("case_sensitive", True))
            present = set(actual_headings) if cs_flag else {h.lower() for h in actual_headings}
            for required in tpl_headings:
                key = required if cs_flag else required.lower()
                if key not in present:
                    if heading_check.get("flag_missing"):
                        issues.append(Issue(SEVERITY_ERROR, slug, "<heading>", "heading_missing", f"missing required heading '## {required}'"))
            if heading_check.get("flag_extra"):
                expected = set(tpl_headings) if cs_flag else {h.lower() for h in tpl_headings}
                for actual in actual_headings:
                    key = actual if cs_flag else actual.lower()
                    if key not in expected:
                        issues.append(Issue(SEVERITY_WARNING, slug, "<heading>", "heading_extra", f"unexpected heading '## {actual}'"))

        # Tag format
        if tag_format_cfg.get("enabled"):
            tags = meta.get("tags")
            tag_pattern = tag_format_cfg.get("pattern")
            if isinstance(tags, list) and isinstance(tag_pattern, str):
                tag_re = re.compile(tag_pattern)
                for t in tags:
                    if not isinstance(t, str) or not tag_re.match(t):
                        issues.append(Issue(SEVERITY_WARNING, slug, "tags", "invalid_tag", f"tag '{t}' does not match pattern {tag_pattern}"))
                if tag_format_cfg.get("require_type_prefix") and isinstance(type_name, str):
                    prefix = (tag_format_cfg.get("type_prefix_map") or {}).get(type_name)
                    if prefix and not any(isinstance(t, str) and t.startswith(prefix) for t in tags):
                        issues.append(Issue(SEVERITY_WARNING, slug, "tags", "missing_type_prefix", f"no tag starts with required prefix '{prefix}'"))

        report.issues.extend(issues)

        # Build flags
        issue_types = _flatten_issue_types(issues)
        oq = meta.get("open_questions") or []
        open_questions_count = len(oq) if isinstance(oq, list) else 0
        flags = {
            "missing_mandatory": "missing_mandatory" in issue_types,
            "invalid_enum": "invalid_enum" in issue_types,
            "invalid_id": "invalid_id" in issue_types,
            "invalid_date": "invalid_date" in issue_types,
            "heading_missing": "heading_missing" in issue_types,
            "overdue_warning": "overdue_warning" in issue_types,
            "overdue_error": "overdue_error" in issue_types,
            "has_open_questions": open_questions_count > 0,
            "low_closure": isinstance(cs, int) and cs < int(low_closure_threshold),
            "never_reviewed": last_reviewed_dt is None,
            "is_draft": meta.get("status") == "draft",
            "is_archived": meta.get("status") in ("archived", "deprecated", "superseded"),
            "is_closed": meta.get("closure_status") == "closed",
        }

        bucket = _bucket_for(flags, color_buckets)

        summary = NoteSummary(
            slug=slug,
            title=str(meta.get("title") or slug),
            type=str(type_name or ""),
            status=meta.get("status") if isinstance(meta.get("status"), str) else None,
            closure_score=cs if isinstance(cs, int) else None,
            closure_status=meta.get("closure_status") if isinstance(meta.get("closure_status"), str) else None,
            review_cycle=review_cycle if isinstance(review_cycle, str) else None,
            last_reviewed=last_reviewed_raw if isinstance(last_reviewed_raw, str) else None,
            days_since_review=days_since,
            days_overdue=days_overdue,
            open_questions_count=open_questions_count,
            issues=issues,
            flags=flags,
            bucket_id=bucket["id"],
            bucket_label=bucket["label"],
            bucket_color=bucket["css_color"],
        )
        report.summaries[slug] = summary

    return report
