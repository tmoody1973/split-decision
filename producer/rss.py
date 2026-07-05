"""Publish pass: episode mp3 -> OSS, regenerate feed.xml (RSS 2.0 + podcast ns).

Published-episode registry lives at episodes/published.json (append-only);
feed.xml is regenerated from it every publish so the feed is always complete.
"""

import email.utils
import json
import sys
import time
from pathlib import Path
from xml.sax.saxutils import escape

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from oss_publish import publish_bytes  # noqa: E402
from producer.episode import Episode, duration_ms  # noqa: E402

REGISTRY_PATH = REPO_ROOT / "episodes" / "published.json"
OSS_BASE = "https://split-decision.oss-ap-southeast-1.aliyuncs.com"

SHOW = {
    "title": "Split Decision",
    "link": f"{OSS_BASE}/site/index.html",
    "description": ("Nine AI jurists with distinct judicial philosophies deliberate real "
                    "Supreme Court cases — argue, persuade, flip votes, and put predictions "
                    "on the record. Two journalist anchors cover the chamber. Every clip of "
                    "deliberation tape is verbatim from the event log."),
    "author": "Split Decision (Qwen Cloud Global AI Hackathon)",
    "language": "en-us",
}


def _duration_str(mp3: Path) -> str:
    secs = duration_ms(mp3) // 1000
    return f"{secs // 3600:02d}:{secs % 3600 // 60:02d}:{secs % 60:02d}"


def load_registry() -> list[dict]:
    return json.loads(REGISTRY_PATH.read_text()) if REGISTRY_PATH.exists() else []


def build_feed(episodes: list[dict]) -> str:
    items = []
    for e in sorted(episodes, key=lambda x: x["pub_date"], reverse=True):
        items.append(f"""    <item>
      <title>{escape(e['title'])}</title>
      <description>{escape(e['description'])}</description>
      <enclosure url="{escape(e['mp3_url'])}" length="{e['bytes']}" type="audio/mpeg"/>
      <guid isPermaLink="false">{escape(e['case_id'])}</guid>
      <pubDate>{e['pub_date']}</pubDate>
      <itunes:duration>{e['duration']}</itunes:duration>
    </item>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd"
     xmlns:podcast="https://podcastindex.org/namespace/1.0">
  <channel>
    <title>{escape(SHOW['title'])}</title>
    <link>{escape(SHOW['link'])}</link>
    <description>{escape(SHOW['description'])}</description>
    <language>{SHOW['language']}</language>
    <itunes:author>{escape(SHOW['author'])}</itunes:author>
    <itunes:explicit>false</itunes:explicit>
    <podcast:medium>podcast</podcast:medium>
{chr(10).join(items)}
  </channel>
</rss>
"""


def publish_episode(ep: Episode, title: str, description: str) -> dict:
    """Upload the mp3, update the registry, regenerate + upload feed.xml."""
    mp3_bytes = ep.mp3_path.read_bytes()
    mp3_url = publish_bytes(mp3_bytes, f"episodes/{ep.case_id}/episode.mp3", "audio/mpeg")

    registry = [e for e in load_registry() if e["case_id"] != ep.case_id]
    registry.append({
        "case_id": ep.case_id, "title": title, "description": description,
        "mp3_url": mp3_url, "bytes": len(mp3_bytes),
        "duration": _duration_str(ep.mp3_path),
        "pub_date": email.utils.formatdate(time.time()),
    })
    REGISTRY_PATH.write_text(json.dumps(registry, indent=2) + "\n")

    feed_url = publish_bytes(build_feed(registry).encode("utf-8"), "feed.xml",
                             "application/rss+xml")
    print(f"mp3:  {mp3_url}\nfeed: {feed_url}")
    return {"mp3_url": mp3_url, "feed_url": feed_url}
