#!/usr/bin/env bash
# Provision a fresh Alibaba Cloud SAS instance as the Split Decision pipeline
# runner (MOO-226). Tested target: Alibaba Cloud Linux 3 (dnf); falls back to
# apt for Ubuntu images. Run as root:
#
#   curl -fsSL https://raw.githubusercontent.com/tmoody1973/split-decision/main/deploy/provision_sas.sh | bash
#   # or: scp this file up, then: bash provision_sas.sh
#
# After it finishes: edit /opt/split-decision/.env (see prompts at the end),
# then: systemctl enable --now split-decision && systemctl status split-decision
set -euo pipefail

REPO_URL="https://github.com/tmoody1973/split-decision.git"
APP_DIR="/opt/split-decision"

echo "== packages =="
if command -v dnf >/dev/null 2>&1; then
  dnf install -y git python3 python3-pip nginx ffmpeg 2>/dev/null || {
    # ffmpeg lives in EPEL on Alibaba Cloud Linux 3
    dnf install -y epel-release || true
    dnf install -y git python3 python3-pip nginx ffmpeg
  }
elif command -v apt-get >/dev/null 2>&1; then
  apt-get update
  apt-get install -y git python3 python3-venv python3-pip nginx ffmpeg
else
  echo "unsupported package manager" >&2
  exit 1
fi

echo "== repo =="
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$APP_DIR"
fi

echo "== venv =="
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --upgrade pip -q
"$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

echo "== env file =="
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  chmod 600 "$APP_DIR/.env"
  echo "NOTE: fill in $APP_DIR/.env — DASHSCOPE_API_KEY, OSS_ACCESS_KEY_ID, OSS_ACCESS_KEY_SECRET"
fi

echo "== systemd unit =="
cp "$APP_DIR/deploy/split-decision.service" /etc/systemd/system/
systemctl daemon-reload

echo "== nginx site (courtroom app) =="
mkdir -p /opt/split-decision-site
cp "$APP_DIR/deploy/nginx-split-decision.conf" /etc/nginx/conf.d/split-decision.conf
# quiet the distro default sites (Ubuntu ships a default_server in sites-enabled)
rm -f /etc/nginx/sites-enabled/default
sed -i 's/ default_server//g' /etc/nginx/nginx.conf 2>/dev/null || true
nginx -t && systemctl enable --now nginx && systemctl reload nginx

echo
echo "Provisioned. Next steps:"
echo "  1. vi $APP_DIR/.env            # paste the three secrets"
echo "  2. systemctl enable --now split-decision"
echo "  3. systemctl status split-decision   # should be: active (exited)"
echo "  4. journalctl -u split-decision -n 30 # shows mp3+feed publish from this instance"
echo "  5. From the dev machine, ship the built app:"
echo "       bash deploy/push_site_to_sas.sh root@<public-ip>"
echo "     then open http://<public-ip>/ in a browser"
