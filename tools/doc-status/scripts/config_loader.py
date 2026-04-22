"""
PURPOSE: Load and validate the YAML configuration files. The single
         responsibility of this module is to make sure no Python script
         elsewhere in the tool defines a default value — every parameter
         comes through here.

OWNS:
  - Resolving config/dashboard.yaml + config/rules.yaml
  - Returning typed dicts (no defaults) so callers crash loudly if a
    required key is missing from YAML

HYPERPARAMETERS:
  - All externalized to config/*.yaml — zero hardcoded values here
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def _config_dir() -> Path:
    env = os.environ.get("DOC_STATUS_CONFIG")
    if not env:
        raise RuntimeError(
            "DOC_STATUS_CONFIG environment variable is required and must "
            "point to the directory containing dashboard.yaml + rules.yaml"
        )
    p = Path(env)
    if not p.is_dir():
        raise RuntimeError(f"DOC_STATUS_CONFIG path does not exist: {p}")
    return p


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Config file missing: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a YAML mapping: {path}")
    return data


def load_dashboard_config() -> dict[str, Any]:
    return load_yaml(_config_dir() / "dashboard.yaml")


def load_rules_config() -> dict[str, Any]:
    return load_yaml(_config_dir() / "rules.yaml")


def load_tests_config() -> dict[str, Any]:
    return load_yaml(_config_dir() / "tests.yaml")


def content_src_dir(dashboard_cfg: dict[str, Any]) -> Path:
    env = os.environ.get("DOC_STATUS_CONTENT")
    if env:
        return Path(env)
    paths = dashboard_cfg.get("paths")
    if not paths or "content_src" not in paths:
        raise KeyError("dashboard.yaml: paths.content_src is required")
    return Path(paths["content_src"])


def require(d: dict[str, Any], key: str, where: str) -> Any:
    if key not in d:
        raise KeyError(f"{where}: required key '{key}' is missing")
    return d[key]
