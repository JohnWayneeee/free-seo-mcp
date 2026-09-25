"""Accumulating CSV keyword store: <data_dir>/<project>/<lang>.csv, one row per phrase."""

import csv
import re
from datetime import UTC, datetime
from pathlib import Path

from .models_research import KeywordRow, StoredKeyword

COLUMNS = [
    "phrase",
    "lang",
    "geo",
    "sources",
    "score",
    "trends_index",
    "bing_impressions",
    "est_volume",
    "tier",
    "cluster",
    "intent",
    "notes",
    "updated_at",
]
_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_NUMERIC = ("score", "trends_index", "est_volume")


def normalize(phrase: str) -> str:
    return " ".join(phrase.lower().split())


def csv_path(data_dir: Path, project: str, lang: str) -> Path:
    for label, value in (("project", project), ("lang", lang)):
        if not _NAME.match(value):
            raise ValueError(
                f"Invalid {label} {value!r}: use 1-64 letters, digits, '-' or '_' "
                "and start with a letter or digit."
            )
    return data_dir / project / f"{lang.lower()}.csv"


def _from_csv(rec: dict[str, str]) -> StoredKeyword:
    data: dict = {k: rec.get(k, "") for k in COLUMNS}
    data["sources"] = [s for s in data["sources"].split("|") if s]
    for k in _NUMERIC:
        data[k] = float(data[k]) if data[k] else None
    data["bing_impressions"] = (
        int(float(data["bing_impressions"])) if data["bing_impressions"] else None
    )
    return StoredKeyword(**data)


def _to_csv(row: StoredKeyword) -> dict[str, str]:
    d = row.model_dump()
    d["sources"] = "|".join(row.sources)
    return {k: "" if d[k] is None else str(d[k]) for k in COLUMNS}


def read(path: Path) -> list[StoredKeyword]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        return [_from_csv(r) for r in csv.DictReader(f)]


def save(
    data_dir: Path, project: str, lang: str, rows: list[KeywordRow]
) -> tuple[Path, int, int, int]:
    """Merge rows into the store. Duplicates match on the normalized phrase: non-empty new
    values overwrite old ones, sources are unioned. Returns (path, added, updated, total)."""
    path = csv_path(data_dir, project, lang)
    existing = {normalize(r.phrase): r for r in read(path)}
    now = datetime.now(UTC).isoformat(timespec="seconds")
    added = updated = 0
    for row in rows:
        key = normalize(row.phrase)
        if not key:
            continue
        incoming = {k: v for k, v in row.model_dump().items() if v not in (None, "", [])}
        incoming["phrase"] = " ".join(row.phrase.split())
        old = existing.get(key)
        if old is None:
            existing[key] = StoredKeyword(**{**incoming, "lang": lang.lower(), "updated_at": now})
            added += 1
            continue
        merged = old.model_dump()
        merged.update(incoming)
        merged["phrase"] = old.phrase
        merged["sources"] = list(dict.fromkeys(old.sources + row.sources))
        merged["updated_at"] = now
        existing[key] = StoredKeyword(**merged)
        updated += 1

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".csv.tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in existing.values():
            w.writerow(_to_csv(r))
    tmp.replace(path)
    return path, added, updated, len(existing)


def load(
    data_dir: Path, project: str, lang: str, tier: str | None = None, cluster: str | None = None
) -> tuple[Path, list[StoredKeyword]]:
    path = csv_path(data_dir, project, lang)
    rows = read(path)
    if tier:
        rows = [r for r in rows if r.tier.lower() == tier.lower()]
    if cluster:
        rows = [r for r in rows if r.cluster.lower() == cluster.lower()]
    return path, rows
