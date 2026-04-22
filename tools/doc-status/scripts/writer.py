"""
PURPOSE: Validate and atomically write a single field back into a note's
         index.meta.json. Preserves key order from the on-disk file
         (insertion order via json.load) and writes 2-space indent + trailing
         newline to match the existing convention.

OWNS:
  - Per-field type coercion driven by rules.yaml.field_types
  - Server-side re-validation against the same rules used for display
  - Atomic write via temp file + os.replace
  - Refusing to touch any field not in rules.yaml.editable_fields

HYPERPARAMETERS:
  - All externalized to config/rules.yaml — zero hardcoded values here
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


class WriterError(ValueError):
    pass


def _coerce(value: Any, field_type: str, rules_cfg: dict[str, Any], field_name: str) -> Any:
    if field_type == "text":
        if not isinstance(value, str):
            raise WriterError(f"{field_name}: expected string, got {type(value).__name__}")
        return value
    if field_type == "textarea":
        if not isinstance(value, str):
            raise WriterError(f"{field_name}: expected string, got {type(value).__name__}")
        return value
    if field_type == "enum":
        enums = rules_cfg.get("enums") or {}
        allowed = enums.get(field_name)
        if not allowed:
            raise WriterError(f"{field_name}: no enum defined in rules.yaml.enums")
        if value not in allowed:
            raise WriterError(f"{field_name}: value '{value}' not in {sorted(allowed)}")
        return value
    if field_type == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise WriterError(f"{field_name}: expected integer, got '{value}'")
        if field_name == "closure_score":
            cmin, cmax = rules_cfg.get("closure_score_range") or [0, 7]
            if value < cmin or value > cmax:
                raise WriterError(f"{field_name}: {value} outside [{cmin}, {cmax}]")
        return value
    if field_type == "date":
        date_format = rules_cfg.get("date_format")
        if not isinstance(value, str):
            raise WriterError(f"{field_name}: expected date string, got {type(value).__name__}")
        if value == "":
            return ""
        try:
            datetime.strptime(value, date_format)
        except ValueError:
            raise WriterError(f"{field_name}: '{value}' does not match date format {date_format}")
        return value
    if field_type == "string_list":
        if isinstance(value, str):
            items = [s.strip() for s in value.split(",") if s.strip()]
        elif isinstance(value, list):
            items = [str(s) for s in value]
        else:
            raise WriterError(f"{field_name}: expected list or comma-separated string")
        if field_name == "tags":
            tag_format = rules_cfg.get("tag_format") or {}
            pattern = tag_format.get("pattern")
            if pattern:
                tag_re = re.compile(pattern)
                for t in items:
                    if not tag_re.match(t):
                        raise WriterError(f"tags: '{t}' does not match {pattern}")
        return items
    raise WriterError(f"{field_name}: unsupported field_type '{field_type}'")


def write_field(meta_path: Path, field_name: str, raw_value: Any, rules_cfg: dict[str, Any]) -> dict[str, Any]:
    editable = rules_cfg.get("editable_fields") or []
    if field_name not in editable:
        raise WriterError(f"field '{field_name}' is not in rules.yaml.editable_fields")

    field_types = rules_cfg.get("field_types") or {}
    field_type = field_types.get(field_name)
    if not field_type:
        raise WriterError(f"field '{field_name}' has no entry in rules.yaml.field_types")

    coerced = _coerce(raw_value, field_type, rules_cfg, field_name)

    if not meta_path.is_file():
        raise WriterError(f"meta path does not exist: {meta_path}")

    with meta_path.open("r", encoding="utf-8") as fh:
        meta = json.load(fh)
    if not isinstance(meta, dict):
        raise WriterError(f"meta JSON is not an object: {meta_path}")

    if field_name in meta:
        meta[field_name] = coerced
    else:
        meta[field_name] = coerced

    serialized = json.dumps(meta, indent=2, ensure_ascii=False)
    if not serialized.endswith("\n"):
        serialized += "\n"

    fd, tmp_name = tempfile.mkstemp(prefix=".doc-status-", suffix=".json.tmp", dir=str(meta_path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_fh:
            tmp_fh.write(serialized)
        os.replace(tmp_name, meta_path)
    except Exception:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise

    return meta
