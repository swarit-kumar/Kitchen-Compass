"""Deterministic, UTF-8 I/O for offline data preparation."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parent.parent


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def read_records(path, schema):
    return [
        schema.model_validate_json(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def index_by(records, attribute):
    index = {}
    for record in records:
        key = getattr(record, attribute)
        if key in index:
            raise ValueError(f"Duplicate {attribute}: {key}")
        index[key] = record
    return index


def write_text(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def write_json(path, payload):
    write_text(path, json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n")


def write_records(path, records):
    write_text(path, "".join(record.model_dump_json() + "\n" for record in records))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
