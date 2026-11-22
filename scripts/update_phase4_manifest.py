
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "artifacts" / "manifest.json"

phase4_inputs = [
    "kitchencompass/adapt.py",
    "tests/test_adapt.py",
    "scripts/check_joint_cases.py",
    "docs/PHASE_4.md",
    "docs/SERVICE_CONTRACT_EXAMPLES.md",
    "HANDOFF.md",
    "scripts/update_phase4_manifest.py",
]

phase4_outputs = [
    "results/development_joint_plans.json",
]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if not MANIFEST.exists():
    raise SystemExit("ERROR: Existing manifest not found.")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

for section in ("input_sha256", "output_sha256"):
    if not isinstance(manifest.get(section), dict):
        raise SystemExit(f"ERROR: Manifest section {section} is missing or invalid.")

for relative_path in phase4_inputs + phase4_outputs:
    if not (ROOT / relative_path).is_file():
        raise SystemExit(f"ERROR: Required file not found: {relative_path}")

for relative_path in phase4_inputs:
    manifest["input_sha256"][relative_path] = sha256(ROOT / relative_path)

for relative_path in phase4_outputs:
    manifest["output_sha256"][relative_path] = sha256(ROOT / relative_path)

manifest["phase4"] = {
    "status": "development_implementation_complete_pending_review",
    "max_targets": 3,
    "max_candidates_per_target": 5,
    "max_combinations": 125,
    "development_cases": 4,
    "evidence_status": "pending_manual_review",
}

MANIFEST.write_text(
    json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
)

print("Phase 4 manifest update successful.")
print("Updated input hashes:", len(phase4_inputs))
print("Updated output hashes:", len(phase4_outputs))
print("Existing manifest entries preserved.")
print("Phase 4 status:", manifest["phase4"]["status"])
