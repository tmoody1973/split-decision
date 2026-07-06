# Deploy — Alibaba Cloud (MOO-226)

Two deploy targets, per `docs/Qwen Cloud Proof of Deployment.md` (the
requirements authority):

1. **OSS static hosting** — courtroom app + episodes + podcast RSS. Live:
   - App: `https://split-decision.oss-ap-southeast-1.aliyuncs.com/site/index.html`
   - Feed: `https://split-decision.oss-ap-southeast-1.aliyuncs.com/feed.xml`
   - Sync script: `deploy/oss_sync_site.py` (uploads `courtroom/dist/**` under `site/`)
2. **SAS (Simple Application Server)** — the pipeline runner
   (`scripts/run_episode.py` behind systemd). This is the compute the proof
   screenshot demonstrates.

## SAS runbook (~15 minutes, console + one script)

1. **Create the instance** — [SAS console](https://www.alibabacloud.com/en/product/swas)
   → Create Server → Region **Singapore (ap-southeast-1)** → Image
   **Alibaba Cloud Linux 3** (or Ubuntu) → smallest plan is fine (pipeline is
   API-bound, no GPU) → pay. Public IP is auto-assigned.
2. **Reset the root password** (console → instance → Reset Password) — SAS has
   no default password.
3. **Connect** — click **Connect** on the instance card (Workbench, no
   password) or `ssh root@<public-ip>`.
4. **Provision** — run:
   ```bash
   curl -fsSL https://raw.githubusercontent.com/tmoody1973/split-decision/main/deploy/provision_sas.sh | bash
   ```
   (installs git/python/ffmpeg, clones the repo to `/opt/split-decision`,
   builds the venv, installs the systemd unit)
5. **Secrets** — `vi /opt/split-decision/.env`: set `DASHSCOPE_API_KEY`,
   `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET` (same values as local `.env`).
   Never commit this file.
6. **Start** —
   ```bash
   systemctl enable --now split-decision
   systemctl status split-decision     # expect: active (exited)
   journalctl -u split-decision -n 30  # shows episode.mp3 + feed.xml publish from the instance
   ```
   The service runs the (idempotent) pipeline publish pass for the hero case
   (`oyez-63889`, Younge) — real OSS writes from Alibaba Cloud compute.
7. **Firewall** — nothing to open; the runner makes outbound calls only
   (default rules TCP 22/80/443 already exceed what we need).

## Proof of deployment (submission artifact)

Per the doc (§ "Sample Screenshot", line ~214): open **Workbench** on the
running instance, show the **Overview** with the running project
(`systemctl status split-decision` output visible is ideal), and screenshot.
Save to `deploy/proof-of-deployment.png`, attach to MOO-226 and the Devpost
submission. Optionally record a short console clip of `journalctl -u
split-decision` scrolling the publish log.

## Notes

- The pipeline needs no inbound port — the courtroom app is served by OSS, not
  the instance. SAS is the compute proof + production runner.
- `provision_sas.sh` is idempotent: re-running pulls the repo and re-installs
  the unit without touching `.env`.
- To produce a brand-new episode from the instance:
  `/opt/split-decision/.venv/bin/python scripts/run_episode.py --case <case_id>`
  (full pass chain: clips → script → tts → timestamps → assemble → publish).
