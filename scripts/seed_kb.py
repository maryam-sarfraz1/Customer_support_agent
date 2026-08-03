"""Seed the knowledge base with the sample dataset.

Usage:
    python scripts/seed_kb.py [--base-url http://localhost:8000] \
        [--email admin@example.com] [--password admin-change-me]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--email", default="admin@example.com")
    parser.add_argument("--password", default="admin-change-me")
    parser.add_argument(
        "--file",
        default=str(Path(__file__).resolve().parent.parent / "data" / "sample_docs.json"),
    )
    args = parser.parse_args()

    payload = json.loads(Path(args.file).read_text(encoding="utf-8"))

    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        login = client.post(
            "/api/v1/auth/login",
            json={"email": args.email, "password": args.password},
        )
        if login.status_code != 200:
            print(f"Login failed ({login.status_code}): {login.text}")
            return 1
        token = login.json()["access_token"]
        resp = client.post(
            "/api/v1/knowledge/ingest",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        if resp.status_code != 200:
            print(f"Ingest failed ({resp.status_code}): {resp.text}")
            return 1
        print(f"Seeded knowledge base: {resp.json()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
