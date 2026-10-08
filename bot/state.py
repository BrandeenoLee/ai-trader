"""Small helpers for reading and writing JSON state files atomically."""
import json
import os
import tempfile
from pathlib import Path

from . import config


def path(name: str) -> Path:
    config.STATE_DIR.mkdir(parents=True, exist_ok=True)
    return config.STATE_DIR / name


def load(name: str, default):
    p = path(name)
    if not p.exists():
        return default
    with p.open() as f:
        return json.load(f)


def save(name: str, data) -> None:
    p = path(name)
    fd, tmp = tempfile.mkstemp(dir=p.parent, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True, default=str)
    os.replace(tmp, p)


def append_jsonl(name: str, record: dict) -> None:
    p = path(name)
    with p.open("a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def read_jsonl(name: str) -> list:
    p = path(name)
    if not p.exists():
        return []
    with p.open() as f:
        return [json.loads(line) for line in f if line.strip()]
