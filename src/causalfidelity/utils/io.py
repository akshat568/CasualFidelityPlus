"""File I/O utilities for CausalFidelity+."""

import json
from pathlib import Path
from typing import Any, Dict, Union

import yaml


def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure that a directory path exists, creating parents if needed.

    Args:
        path: Target directory path.

    Returns:
        Path object of the ensured directory.
    """
    target_path = Path(path)
    target_path.mkdir(parents=True, exist_ok=True)
    return target_path


def load_yaml(path: Union[str, Path]) -> Dict[str, Any]:
    """Load content from a YAML file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed dictionary content.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"YAML file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml(data: Dict[str, Any], path: Union[str, Path]) -> None:
    """Save dictionary content to a YAML file.

    Args:
        data: Dictionary content to write.
        path: Target file path.
    """
    file_path = Path(path)
    ensure_dir(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)


def load_json(path: Union[str, Path]) -> Dict[str, Any]:
    """Load content from a JSON file.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed dictionary or list content.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: Union[str, Path], indent: int = 2) -> None:
    """Save data to a JSON file.

    Args:
        data: Data content to write.
        path: Target file path.
        indent: JSON indentation depth.
    """
    file_path = Path(path)
    ensure_dir(file_path.parent)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
