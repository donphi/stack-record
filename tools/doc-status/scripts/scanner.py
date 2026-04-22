"""
PURPOSE: Walk content_src, load every index.meta.json, every folder
         meta.json, every index.mdx (for headings), and every per-type
         _template/example.{mdx,meta.json}.template.

OWNS:
  - Filesystem traversal (os.walk)
  - Stripping Fumadocs folder-group segments (parenthesized dirs) from slugs
  - Reading raw bytes and JSON for each note
  - Extracting `## ` headings from MDX bodies in document order
  - Loading the per-type template once at startup, cached by note type

HYPERPARAMETERS:
  - All externalized to config/dashboard.yaml + config/rules.yaml
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
FOLDER_GROUP_PATTERN = re.compile(r"^\(\d+-[^)]+\)$|^\([^)]+\)$")


@dataclass
class Note:
    slug: str
    abs_meta_path: Path
    abs_mdx_path: Path | None
    rel_dir: str
    meta_raw_bytes: bytes
    meta: dict[str, Any]
    headings: list[str]


@dataclass
class Folder:
    folder_path: str
    abs_path: Path
    parent_path: str | None
    meta: dict[str, Any]


@dataclass
class TypeTemplate:
    type_name: str
    template_dir: Path
    meta_template: dict[str, Any]
    headings: list[str]


@dataclass
class ScanResult:
    content_src: Path
    notes: dict[str, Note] = field(default_factory=dict)
    folders: dict[str, Folder] = field(default_factory=dict)
    templates: dict[str, TypeTemplate] = field(default_factory=dict)


def slug_from_rel_dir(rel_dir: str) -> str:
    parts = []
    for seg in Path(rel_dir).parts:
        if FOLDER_GROUP_PATTERN.match(seg):
            continue
        parts.append(seg)
    return "/".join(parts) if parts else ""


def extract_headings(mdx_text: str) -> list[str]:
    return [m.group(1).strip() for m in HEADING_PATTERN.finditer(mdx_text)]


def _load_json(path: Path) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    obj = json.loads(raw.decode("utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"meta JSON must be an object: {path}")
    return raw, obj


def _is_under_template(rel_dir: str) -> bool:
    return any(seg == "_template" for seg in Path(rel_dir).parts)


def load_type_templates(content_src: Path, rules_cfg: dict[str, Any]) -> dict[str, TypeTemplate]:
    note_types = rules_cfg.get("note_types")
    if not isinstance(note_types, dict) or not note_types:
        raise KeyError("rules.yaml: note_types mapping is required")

    out: dict[str, TypeTemplate] = {}
    for type_name, type_cfg in note_types.items():
        if "template_dir" not in type_cfg:
            raise KeyError(f"rules.yaml: note_types.{type_name}.template_dir missing")
        tdir = content_src / type_cfg["template_dir"]
        meta_path = tdir / "example.meta.json.template"
        mdx_path = tdir / "example.mdx.template"
        if not meta_path.is_file():
            raise FileNotFoundError(f"missing meta template for type '{type_name}': {meta_path}")
        if not mdx_path.is_file():
            raise FileNotFoundError(f"missing mdx template for type '{type_name}': {mdx_path}")
        with meta_path.open("r", encoding="utf-8") as fh:
            meta_template = json.load(fh)
        mdx_text = mdx_path.read_text(encoding="utf-8")
        out[type_name] = TypeTemplate(
            type_name=type_name,
            template_dir=tdir,
            meta_template=meta_template,
            headings=extract_headings(mdx_text),
        )
    return out


def scan(content_src: Path, rules_cfg: dict[str, Any]) -> ScanResult:
    if not content_src.is_dir():
        raise FileNotFoundError(f"content_src directory does not exist: {content_src}")

    result = ScanResult(content_src=content_src)
    result.templates = load_type_templates(content_src, rules_cfg)

    for root, dirs, files in os.walk(content_src):
        dirs.sort()
        files.sort()
        rel_dir = os.path.relpath(root, content_src)
        if rel_dir == ".":
            rel_dir = ""

        if _is_under_template(rel_dir):
            continue

        if "meta.json" in files:
            meta_path = Path(root) / "meta.json"
            try:
                _raw, meta_obj = _load_json(meta_path)
            except json.JSONDecodeError as exc:
                meta_obj = {"_parse_error": str(exc)}
            folder_path = slug_from_rel_dir(rel_dir)
            parent_path = "/".join(folder_path.split("/")[:-1]) if folder_path else None
            if parent_path == "":
                parent_path = None
            result.folders[folder_path] = Folder(
                folder_path=folder_path,
                abs_path=Path(root),
                parent_path=parent_path,
                meta=meta_obj,
            )

        if "index.meta.json" in files:
            meta_path = Path(root) / "index.meta.json"
            mdx_path = Path(root) / "index.mdx"
            try:
                raw, meta_obj = _load_json(meta_path)
            except json.JSONDecodeError as exc:
                raw = meta_path.read_bytes()
                meta_obj = {"_parse_error": str(exc)}
            headings: list[str] = []
            if mdx_path.is_file():
                headings = extract_headings(mdx_path.read_text(encoding="utf-8"))
            slug = slug_from_rel_dir(rel_dir)
            note = Note(
                slug=slug,
                abs_meta_path=meta_path,
                abs_mdx_path=mdx_path if mdx_path.is_file() else None,
                rel_dir=rel_dir,
                meta_raw_bytes=raw,
                meta=meta_obj,
                headings=headings,
            )
            result.notes[slug] = note

    return result
