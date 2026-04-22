"""
Smoke test: scanning + validating the REAL content tree must not crash.
This proves the validator handles every existing per-type template
format and every actual note. Read-only.

Uses date.today() (the validator default) — no frozen reference date.

Skipped when the real content tree is not present (e.g. local run
without the docker mount or without the relative fallback).
"""

from __future__ import annotations

import pytest


def test_scanner_and_validator_handle_real_tree(real_content_src, configured_env, monkeypatch, dashboard_cfg, rules_cfg):
    monkeypatch.setenv("DOC_STATUS_CONTENT", str(real_content_src))

    from scanner import scan
    from validator import validate

    result = scan(real_content_src, rules_cfg)
    assert result.notes, "scanner found zero notes in the real content tree"
    assert set(result.templates.keys()) == set(rules_cfg["note_types"].keys()), \
        "real content tree is missing a _template/ for one of the declared note_types"

    report = validate(result, rules_cfg, dashboard_cfg)
    assert report.summaries
    allowed_buckets = {b["id"] for b in dashboard_cfg["color_buckets"]}
    for slug, summary in report.summaries.items():
        assert summary.bucket_id in allowed_buckets, \
            f"{slug}: unexpected bucket {summary.bucket_id}"
