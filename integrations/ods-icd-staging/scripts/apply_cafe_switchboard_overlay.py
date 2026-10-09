"""Apply the small, reviewed cafe-llama switchboard delta to a fresh ODS checkout.

This staging patch is deliberately fail-closed: it aborts if upstream has moved
the expected seams, instead of silently applying a partial or stale patch.
"""
from pathlib import Path
import json

ROOT = Path("ods-src/ods")


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected one patch anchor, found {count}: {old[:90]!r}")
    path.write_text(text.replace(old, new, 1))


# State writer and published schema must agree about writable provider IDs.
replace_once(
    ROOT / "bin/model_switchboard/state.py",
    '_WRITABLE_BACKEND_KINDS = {"llama-server", "hipfire", "unknown"}',
    '_WRITABLE_BACKEND_KINDS = {"llama-server", "cafe-llama", "hipfire", "unknown"}',
)
schema_path = ROOT / "config/model-state.schema.v1.json"
replace_once(
    schema_path,
    '"enum": ["llama-server", "lemonade", "hipfire", "unknown"]',
    '"enum": ["llama-server", "cafe-llama", "lemonade", "hipfire", "unknown"]',
)

# The endpoint is available only to an explicitly activated cafe runtime.
endpoint_path = ROOT / "config/model-router/endpoints.json"
doc = json.loads(endpoint_path.read_text())
endpoints = doc.get("endpoints")
if not isinstance(endpoints, list):
    raise SystemExit("model-router endpoints must be a list")
cafe = [entry for entry in endpoints if isinstance(entry, dict) and entry.get("id") == "cafe-llama-default"]
if cafe:
    if cafe[0].get("baseUrl") != "http://cafe-llama:8081":
        raise SystemExit("existing cafe endpoint conflicts with the pinned endpoint contract")
else:
    endpoints.append({"id": "cafe-llama-default", "baseUrl": "http://cafe-llama:8081"})
    endpoint_path.write_text(json.dumps(doc, indent=2) + "\n")

# Reconciler must not discard the runtime provenance that the cafe adapter proves.
reconciler_path = ROOT / "bin/model_switchboard/reconciler.py"
replace_once(
    reconciler_path,
    '            outcome_proof = {\n                "identity": outcome_identity,\n                "contextLength": int(outcome["contextLength"]),\n                "contextVerified": bool(outcome["contextVerified"]),\n                "capabilities": dict(outcome["capabilities"]),\n                "verifiedAt": str(outcome["verifiedAt"]),\n            }\n            stable_fields = (\n                "identity",\n                "contextLength",\n                "contextVerified",\n                "capabilities",\n            )',
    '            outcome_proof = {\n                "identity": outcome_identity,\n                "contextLength": int(outcome["contextLength"]),\n                "contextVerified": bool(outcome["contextVerified"]),\n                "capabilities": dict(outcome["capabilities"]),\n                "verifiedAt": str(outcome["verifiedAt"]),\n            }\n            if getattr(adapter, "kind", None) == "cafe-llama":\n                build_id = outcome.get("runtimeBuildId")\n                digest = outcome.get("artifactSha256")\n                if (\n                    outcome.get("runtimeKind") != "cafe-llama"\n                    or not isinstance(build_id, str) or not build_id.strip()\n                    or not isinstance(digest, str) or len(digest) != 64\n                    or any(char not in "0123456789abcdef" for char in digest)\n                ):\n                    return {\n                        "ok": False, "phase": phase,\n                        "detail": "cafe runtime proof is missing build identity or artifact digest",\n                        **proof,\n                    }\n                outcome_proof.update(runtimeKind="cafe-llama", runtimeBuildId=build_id, artifactSha256=digest)\n            stable_fields = (\n                "identity",\n                "contextLength",\n                "contextVerified",\n                "capabilities",\n                "runtimeKind",\n                "runtimeBuildId",\n                "artifactSha256",\n            )',
)
print("Applied cafe-llama state/schema/endpoint/provenance overlay.")
