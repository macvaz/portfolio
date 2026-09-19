#!/usr/bin/env python3
"""Resolve Category.fund_id → performance_id and update categories.json."""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import requests

DETAILS_URL = "https://lt.morningstar.com/api/rest.svc/security_details/t92wz0sj7c"
HEADERS = {"User-Agent": "Mozilla/5.0", "Accept": "*/*"}


def resolve_performance_id(fund_id: str, *, attempts: int = 4) -> str | None:
    for attempt in range(attempts):
        response = requests.get(
            DETAILS_URL,
            params={"id": fund_id, "idtype": "Morningstar", "outputType": "JSON"},
            headers=HEADERS,
            timeout=60,
        )
        text = response.text or ""
        if text:
            for pattern in (r'PerformanceId="([^"]+)"', r'_PerformanceId="([^"]+)"'):
                match = re.search(pattern, text)
                if match and match.group(1).strip():
                    return match.group(1).strip()
            # nonempty payload but no PerformanceId
            return None
        time.sleep(0.4 * (attempt + 1))
    return None


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "data/fixtures/categories.json")
    rows = json.loads(path.read_text(encoding="utf-8"))
    cache: dict[str, str | None] = {}
    ok = miss = skip = 0
    unique_ids = sorted({str(r["fund_id"]) for r in rows if r.get("fund_id")})
    print(f"Resolving {len(unique_ids)} unique fund_ids…", flush=True)
    for index, fund_id in enumerate(unique_ids, start=1):
        try:
            cache[fund_id] = resolve_performance_id(fund_id)
        except Exception as exc:  # noqa: BLE001
            print(f"ERR {fund_id}: {exc}", flush=True)
            cache[fund_id] = None
        time.sleep(0.15)
        if index % 25 == 0 or index == len(unique_ids):
            resolved = sum(1 for v in cache.values() if v)
            print(
                f"lookup {index}/{len(unique_ids)} resolved={resolved} empty={index-resolved}",
                flush=True,
            )

    for row in rows:
        fund_id = row.get("fund_id")
        if not fund_id:
            row["performance_id"] = None
            skip += 1
            continue
        performance_id = cache.get(str(fund_id))
        row["performance_id"] = performance_id
        if performance_id:
            ok += 1
        else:
            miss += 1

    path.write_text(
        json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"DONE {path} ok={ok} miss={miss} skip={skip}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
