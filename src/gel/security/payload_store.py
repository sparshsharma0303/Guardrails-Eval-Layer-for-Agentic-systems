import hashlib
import json
from pathlib import Path

from gel.security.payloads import PayloadRegistry


def compute_registry_hash(registry: PayloadRegistry) -> str:
    """Compute a deterministic SHA-256 hash of a security payload registry."""

    payloads = [payload.model_dump(mode="json") for payload in registry.payloads]
    combined = {
        "registry_id": registry.registry_id,
        "registry_version": registry.registry_version,
        "payloads": payloads,
    }
    canonical_json = json.dumps(
        combined,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_json.encode()).hexdigest()


def save_registry(
    registry: PayloadRegistry,
    directory: str | Path = "datasets",
) -> Path:
    """Save a security payload registry as versioned JSON."""

    directory_path = Path(directory)
    filename = f"{registry.registry_id}__v{registry.registry_version}.json"
    file_path = directory_path / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)
    json_data = registry.model_dump_json(indent=2)
    with file_path.open("x", encoding="utf-8") as f:
        f.write(json_data)
    return file_path


def load_registry(path: str | Path) -> PayloadRegistry:
    """Load a security payload registry from JSON."""

    text = Path(path).read_text(encoding="utf-8")
    return PayloadRegistry.model_validate_json(text)
