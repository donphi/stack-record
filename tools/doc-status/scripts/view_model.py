"""
PURPOSE: Build the in-memory view model used by both the live server and the
         one-shot static / markdown exporters. Keeps formatting concerns out
         of scanner.py and validator.py.

OWNS:
  - Folder→note tree assembly
  - Per-folder bucket roll-up counts
  - Filter preset application
  - Aggregate counts (bucket totals, total issues)

HYPERPARAMETERS:
  - All externalized to config/dashboard.yaml + config/rules.yaml
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from scanner import ScanResult, Folder
from validator import NoteSummary, ValidationReport


@dataclass
class TreeNode:
    kind: str               # "folder" or "note"
    title: str
    path: str
    children: list["TreeNode"] = field(default_factory=list)
    summary: NoteSummary | None = None
    bucket_counts: dict[str, int] = field(default_factory=dict)


def _folder_title(folder_path: str, folders: dict[str, Folder]) -> str:
    if folder_path in folders:
        meta = folders[folder_path].meta
        if isinstance(meta, dict) and isinstance(meta.get("title"), str) and meta["title"]:
            return meta["title"]
    return folder_path.split("/")[-1] if folder_path else "/"


def build_tree(scan: ScanResult, report: ValidationReport, color_buckets: list[dict[str, Any]]) -> TreeNode:
    bucket_ids = [b["id"] for b in color_buckets]
    root = TreeNode(kind="folder", title="/", path="")
    folder_nodes: dict[str, TreeNode] = {"": root}

    all_folder_paths = set(scan.folders.keys())
    for slug in scan.notes:
        parts = slug.split("/") if slug else []
        for i in range(len(parts)):
            all_folder_paths.add("/".join(parts[:i]))

    for path in sorted(all_folder_paths):
        if path == "":
            continue
        if path in folder_nodes:
            continue
        title = _folder_title(path, scan.folders)
        node = TreeNode(kind="folder", title=title, path=path)
        parent_path = "/".join(path.split("/")[:-1])
        parent = folder_nodes.setdefault(parent_path, TreeNode(kind="folder", title=parent_path or "/", path=parent_path))
        parent.children.append(node)
        folder_nodes[path] = node

    for slug, summary in sorted(report.summaries.items()):
        parts = slug.split("/") if slug else []
        parent_path = "/".join(parts[:-1]) if parts else ""
        parent = folder_nodes.get(parent_path)
        if parent is None:
            parent = root
        leaf = TreeNode(kind="note", title=summary.title, path=slug, summary=summary)
        parent.children.append(leaf)

    def _walk(node: TreeNode) -> dict[str, int]:
        counts = {bid: 0 for bid in bucket_ids}
        for child in node.children:
            if child.kind == "note" and child.summary is not None:
                counts[child.summary.bucket_id] = counts.get(child.summary.bucket_id, 0) + 1
            else:
                child_counts = _walk(child)
                for k, v in child_counts.items():
                    counts[k] = counts.get(k, 0) + v
        node.bucket_counts = counts
        return counts

    _walk(root)
    return root


def filter_summaries(summaries: dict[str, NoteSummary], preset: dict[str, Any] | None, q: str | None, type_filter: str | None) -> list[NoteSummary]:
    where = (preset or {}).get("where", {}) if preset else {}
    out: list[NoteSummary] = []
    for s in summaries.values():
        if type_filter and s.type != type_filter:
            continue
        if q:
            ql = q.lower()
            if ql not in s.title.lower() and ql not in s.slug.lower():
                continue
        if "bucket" in where and s.bucket_id not in where["bucket"]:
            continue
        if where.get("overdue") and not (s.flags.get("overdue_warning") or s.flags.get("overdue_error")):
            continue
        if "has_issue" in where:
            wanted = set(where["has_issue"])
            actual = {i.issue_type for i in s.issues}
            if not (wanted & actual):
                continue
        if "open_questions_min" in where and s.open_questions_count < where["open_questions_min"]:
            continue
        if "status" in where and s.status not in where["status"]:
            continue
        out.append(s)
    return out


def _sort_value(summary: NoteSummary, field_name: str) -> Any:
    """Return the comparable value for a summary on a given sortable field.
    'issue_count' is derived; everything else is a NoteSummary attribute."""
    if field_name == "issue_count":
        return len(summary.issues)
    return getattr(summary, field_name, None)


def sort_summaries(summaries: list[NoteSummary], sort_id: str | None, direction: str | None, sortable_columns: list[dict[str, Any]]) -> list[NoteSummary]:
    """Sort by a configured sortable column. Notes with None/missing values
    for the chosen field go to the END regardless of direction. When sort_id
    is None or not declared in sortable_columns, falls back to (bucket, slug).
    """
    config = next((c for c in sortable_columns if c["id"] == sort_id), None) if sort_id else None
    if config is None:
        return sorted(summaries, key=lambda s: (s.bucket_id, s.slug))

    field_name = config["field"]
    direction = (direction or config.get("default_direction") or "desc").lower()
    reverse = direction == "desc"

    with_value: list[tuple[Any, NoteSummary]] = []
    without_value: list[NoteSummary] = []
    for s in summaries:
        v = _sort_value(s, field_name)
        if v is None:
            without_value.append(s)
        else:
            with_value.append((v, s))

    with_value.sort(key=lambda pair: pair[0], reverse=reverse)
    without_value.sort(key=lambda s: s.slug)
    return [s for _, s in with_value] + without_value


def next_sort_direction(active_sort_id: str | None, active_direction: str | None, column_id: str, default_direction: str) -> str:
    """Three-click cycle: default → opposite → default again. Same column
    only — clicking a different column resets to that column's default."""
    if active_sort_id != column_id:
        return default_direction
    opposite = "asc" if (active_direction or default_direction) == "desc" else "desc"
    return opposite if active_direction == default_direction else default_direction


def bucket_totals(summaries: dict[str, NoteSummary], bucket_ids: list[str]) -> dict[str, int]:
    counts = {bid: 0 for bid in bucket_ids}
    for s in summaries.values():
        counts[s.bucket_id] = counts.get(s.bucket_id, 0) + 1
    return counts
