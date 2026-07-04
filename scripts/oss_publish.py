"""Generate -> download -> OSS in one function (MOO-218).

Provider image URLs expire in 24h (CLAUDE.md §0.6), so anything generated is
pushed to OSS in the same function that created it. This module is the
reusable publishing leg for the art pass, podcast MP3s, and RSS.

Usage (round-trip test): python scripts/oss_publish.py
"""

import os
import sys
import time
from pathlib import Path

import oss2
import requests

from qwen_client import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
OSS_ENDPOINT = "https://oss-ap-southeast-1.aliyuncs.com"


def oss_bucket() -> oss2.Bucket:
    load_dotenv()
    auth = oss2.Auth(os.environ["OSS_ACCESS_KEY_ID"], os.environ["OSS_ACCESS_KEY_SECRET"])
    return oss2.Bucket(auth, OSS_ENDPOINT, os.environ.get("OSS_BUCKET", "split-decision"))


def publish_bytes(data: bytes, key: str, content_type: str) -> str:
    """Upload bytes to OSS; return the public URL."""
    bucket = oss_bucket()
    bucket.put_object(key, data, headers={"Content-Type": content_type, "x-oss-object-acl": "public-read"})
    return f"https://{bucket.bucket_name}.oss-ap-southeast-1.aliyuncs.com/{key}"


def publish_url(source_url: str, key: str, content_type: str) -> str:
    """Download a (short-lived) provider URL and republish it to OSS."""
    resp = requests.get(source_url, timeout=300)
    resp.raise_for_status()
    return publish_bytes(resp.content, key, content_type)


DASHSCOPE_NATIVE = "https://dashscope-intl.aliyuncs.com/api/v1"


def generate_image_to_oss(prompt: str, key: str, size: str = "1024*576",
                          model: str = "wan2.6-t2i") -> str:
    """Image generation -> immediate OSS publish, one function.

    Route verified live 2026-07-04: wan2.6-t2i serves on the SYNC multimodal
    endpoint (the OpenAI-compatible /images route 404s, and the async
    text2image route rejects wan2.6 with 'url error').
    """
    load_dotenv()
    resp = requests.post(
        f"{DASHSCOPE_NATIVE}/services/aigc/multimodal-generation/generation",
        headers={
            "Authorization": f"Bearer {os.environ['DASHSCOPE_API_KEY']}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "input": {"messages": [{"role": "user", "content": [{"text": prompt}]}]},
            "parameters": {"size": size},
        },
        timeout=300,
    )
    resp.raise_for_status()
    body = resp.json()
    content = body["output"]["choices"][0]["message"]["content"]
    image_url = next(part["image"] for part in content if part.get("type") == "image")
    return publish_url(image_url, key, "image/png")


if __name__ == "__main__":
    url = generate_image_to_oss(
        "Hand-drawn courtroom sketch, warm pastel, loose ink lines: nine robed "
        "jurists at a long bench, one gesturing mid-argument, tall windows.",
        key=f"test/roundtrip_{int(time.time())}.png",
    )
    print(f"public URL: {url}")
    check = requests.get(url, timeout=60)
    print(f"public fetch: HTTP {check.status_code}, {len(check.content)} bytes, "
          f"{check.headers.get('content-type')}")
    sys.exit(0 if check.status_code == 200 else 1)
