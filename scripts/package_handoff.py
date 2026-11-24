"""Package the verified Phase 5 snapshot from its file manifest."""
import argparse
import hashlib
import os
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from kitchencompass.data_io import ROOT, read_json


def package(output):
    manifest_path = "artifacts/manifest.json"
    manifest = read_json(ROOT / manifest_path)
    files = {**manifest["input_sha256"], **manifest["output_sha256"], manifest_path: None}
    output.mkdir(parents=True, exist_ok=True)
    destination = output / "KitchenCompass_P05_v0.6.0_20261123.zip"
    fd, name = tempfile.mkstemp(dir=output)
    os.close(fd)
    try:
        with ZipFile(name, "w") as archive:
            for path, expected in sorted(files.items()):
                data = (ROOT / path).read_bytes()
                if expected is not None and hashlib.sha256(data).hexdigest() != expected:
                    raise ValueError(f"Hash mismatch for {path}. Rebuild the features and manifest.")
                entry = ZipInfo("KitchenCompass_Phase5_v0.6.0/" + path)
                entry.compress_type = ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                entry.create_system = 3
                archive.writestr(entry, data)
        os.replace(name, destination)
    finally:
        Path(name).unlink(missing_ok=True)
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", type=int, choices=[5], default=5)
    parser.add_argument("--output", type=Path, default=Path("dist"))
    print(package(parser.parse_args().output))
