#!/usr/bin/env python3
"""
Rebuild manifest.json from provider model files.
"""

import json
from pathlib import Path
from datetime import datetime

data_dir = Path(__file__).parent.parent / "data"
models_dir = data_dir / "models"

if not models_dir.exists():
    raise SystemExit(f"Models directory not found: {models_dir}")

# Gather all provider files
provider_files = []
for path in sorted(models_dir.rglob("*.json")):
    if path.is_file():
        provider_files.append(str(path.relative_to(data_dir)))

# Create manifest.json
manifest = {
    "model_files": provider_files,
    "last_updated": datetime.now().isoformat()
}

manifest_path = data_dir / "manifest.json"
with open(manifest_path, "w") as f:
    json.dump(manifest, f, indent=2)

print(f"✓ Updated manifest.json with {len(provider_files)} provider files")
