# Deploy — Alibaba Cloud (MOO-226)

Requirements authority: `docs/Qwen Cloud Proof of Deployment.md`.

Two Alibaba Cloud surfaces:

1. **SAS (Simple Application Server)** — runs BOTH the pipeline
   (`scripts/run_episode.py` behind systemd) and the public courtroom app
   (nginx, port 80). This is the compute the proof screenshot demonstrates.
2. **OSS** — podcast storage: episode MP3s, art, and the RSS feed. Live:
   - Feed: `https://split-decision.oss-ap-southeast-1.aliyuncs.com/feed.xml`
   - Enclosures: `.../episodes/<case_id>/episode.mp3`

> **Why the app is NOT on OSS static hosting** (discovered 2026-07-06): the OSS
> default endpoint force-downloads web content — every `site/` object returns
> `Content-Disposition: attachment` + `x-oss-force-download: true`, and an
> explicit `Content-Disposition: inline` upload header is overridden (verified
> live). Alibaba's bypass is binding a custom domain, which MOO-226 rules out
> of scope. Podcast enclosures are unaffected (clients ignore the header), so
> OSS keeps the feed; the browser app moves to nginx on the SAS instance.

## SAS runbook (~15 minutes, console + two scripts)

1. **Create the instance** — [SAS console](https://www.alibabacloud.com/en/product/swas)
   → Create Server → Region **Singapore (ap-southeast-1)** → Image
   **Alibaba Cloud Linux 3** (or Ubuntu) → smallest plan is fine (pipeline is
   API-bound, no GPU; app is static files) → pay. Public IP auto-assigned.
2. **Reset the root password** (console → instance → Reset Password) — SAS has
   no default password.
3. **Connect** — click **Connect** on the instance card (Workbench, no
   password) or `ssh root@<public-ip>`.
4. **Provision** — on the instance:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/tmoody1973/split-decision/main/deploy/provision_sas.sh | bash
   ```
   (installs git/python/nginx/ffmpeg, clones the repo to `/opt/split-decision`,
   builds the venv, installs the systemd unit + nginx site)
5. **Secrets** — `vi /opt/split-decision/.env`: set `DASHSCOPE_API_KEY`,
   `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET` (same values as local `.env`).
   Never commit this file.
6. **Start the pipeline service** —
   ```bash
   systemctl enable --now split-decision
   systemctl status split-decision     # expect: active (exited)
   journalctl -u split-decision -n 30  # shows episode.mp3 + feed.xml publish from the instance
   ```
   The service runs the (idempotent) publish pass for the hero case
   (`oyez-63889`, Younge) — real OSS writes from Alibaba Cloud compute.
7. **Ship the app** — from the dev machine (dist is built locally; the repo
   does not track it):
   ```bash
   cd courtroom && npm run build && cd ..
   bash deploy/push_site_to_sas.sh root@<public-ip>
   ```
   Then open `http://<public-ip>/` — landing page; hero replay at
   `http://<public-ip>/courtroom.html?episode=oyez-63889`.
8. **Firewall** — default rules already allow TCP 80; nothing to add.

## Proof of deployment (submission artifact)

Per the doc (§ "Sample Screenshot"): open **Workbench** on the running
instance, show the **Overview** with the running project — ideally with
`systemctl status split-decision nginx` output visible — and screenshot. Save
to `deploy/proof-of-deployment.png`, attach to MOO-226 and the Devpost
submission. Optionally record a short console clip of
`journalctl -u split-decision` scrolling the publish log.

## Files

| File | Purpose |
| --- | --- |
| `provision_sas.sh` | one-shot instance setup (idempotent) |
| `split-decision.service` | systemd unit — pipeline publish pass, hero case |
| `nginx-split-decision.conf` | nginx site for the courtroom app |
| `push_site_to_sas.sh` | rsync `courtroom/dist` → instance web root |
| `oss_sync_site.py` | legacy OSS `site/` upload (kept for asset storage; not the app host) |

## Notes

- To produce a brand-new episode from the instance:
  `/opt/split-decision/.venv/bin/python scripts/run_episode.py --case <case_id>`
  (full chain: clips → script → tts → timestamps → assemble → publish).
- `provision_sas.sh` re-runs safely: pulls the repo, re-installs unit + nginx
  config, never touches `.env`.
