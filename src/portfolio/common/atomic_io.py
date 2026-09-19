"""Atomic filesystem helpers for durable CSV updates."""

from pathlib import Path

import pandas as pd


def atomic_to_csv(path: Path, df: pd.DataFrame) -> None:
    """Write ``df`` to ``path`` via a temp file so crashes never blank the old CSV.

    Opens ``path.with_suffix(path.suffix + ".tmp")``, writes fully, then
    ``Path.replace`` onto ``path``. On failure the previous ``path`` is left
    untouched and the temp file is removed when possible.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    try:
        df.to_csv(tmp_path, index=False)
        tmp_path.replace(path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
