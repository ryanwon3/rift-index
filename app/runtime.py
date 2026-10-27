from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

from app.config import DATA_DIR, DATASET_COMMIT


def runtime_chroma_path(
    data_dir: Path = DATA_DIR,
    *,
    is_vercel: bool | None = None,
    temp_root: Path | None = None,
) -> Path:
    source = data_dir / "chroma"
    vercel_runtime = os.environ.get("VERCEL") == "1" if is_vercel is None else is_vercel
    if not vercel_runtime:
        return source
    if not source.is_dir():
        raise RuntimeError(f"bundled Chroma index is missing: {source}")

    scratch_root = temp_root or Path(tempfile.gettempdir())
    deployment_root = scratch_root / f"rift-index-{DATASET_COMMIT[:12]}"
    target = deployment_root / "chroma"
    if target.is_dir():
        return target

    deployment_root.mkdir(parents=True, exist_ok=True)
    staging = deployment_root / f".chroma-{os.getpid()}"
    if staging.exists():
        shutil.rmtree(staging)
    shutil.copytree(source, staging)
    try:
        staging.rename(target)
    except FileExistsError:
        if not target.is_dir():
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target
