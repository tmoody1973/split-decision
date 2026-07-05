"""Deploy the built courtroom web app to OSS static hosting (MOO-226).

Uploads courtroom/dist/** to the public bucket under site/, with correct
content types and public-read ACLs. The app is fully static and built with
relative asset paths, so direct object URLs serve it as-is.

Usage: .venv/bin/python deploy/oss_sync_site.py
"""

import mimetypes
import sys
from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from oss_publish import oss_bucket  # noqa: E402

DIST = REPO_ROOT / "courtroom" / "dist"
PREFIX = "site"

EXTRA_TYPES = {
    ".jsonl": "application/x-ndjson",
    ".mp3": "audio/mpeg",
    ".ts": "video/mp2t",  # never shipped, defensive
}


def content_type(path: Path) -> str:
    if path.suffix in EXTRA_TYPES:
        return EXTRA_TYPES[path.suffix]
    guessed, _ = mimetypes.guess_type(str(path))
    return guessed or "application/octet-stream"


def main() -> int:
    if not DIST.exists():
        raise SystemExit("courtroom/dist missing — run `npm run build` first")
    bucket = oss_bucket()
    files = sorted(p for p in DIST.rglob("*") if p.is_file())
    total = 0
    for path in files:
        key = f"{PREFIX}/{path.relative_to(DIST).as_posix()}"
        bucket.put_object_from_file(
            key, str(path),
            headers={"Content-Type": content_type(path), "x-oss-object-acl": "public-read"},
        )
        total += path.stat().st_size
        print(f"  {key} ({path.stat().st_size / 1024:.0f} KB)")
    url = f"https://{bucket.bucket_name}.oss-ap-southeast-1.aliyuncs.com/{PREFIX}/index.html"
    print(f"\nuploaded {len(files)} files, {total / 1048576:.1f} MB")
    check = requests.get(url, timeout=60)
    print(f"public fetch: HTTP {check.status_code} {check.headers.get('content-type')}")
    print(f"LIVE: {url}")
    return 0 if check.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
