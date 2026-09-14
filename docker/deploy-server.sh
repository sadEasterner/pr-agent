#!/bin/bash
set -euo pipefail
cd /root/hosein/pr-manager

echo "==> disk"
df -h / | tail -1

echo "==> load images"
rm -f pr-manager-images.tar
gzip -dk pr-manager-images.tar.gz
docker load -i pr-manager-images.tar
rm -f pr-manager-images.tar pr-manager-images.tar.gz
docker images | grep -E "pr-mangement|REPOSITORY" || true

echo "==> production env"
sed -i 's/^APP_ENV=.*/APP_ENV=production/' .env
grep -E '^(APP_ENV|GITEA_BASE_URL|AI_PROVIDER|AI_ENABLED)=' .env

echo "==> compose up"
docker compose -f docker-compose.prod.yml up -d
sleep 8
docker compose -f docker-compose.prod.yml ps

echo "==> nginx snippet"
install -m 644 /root/hosein/pr-manager/pr-manager.hosein.work.conf /etc/nginx/snippets/pr-manager.conf
python3 - <<'PY'
from pathlib import Path
path = Path("/etc/nginx/sites-enabled/hosein.work.conf")
text = path.read_text()
needle = "    include /etc/nginx/snippets/pr-manager.conf;\n"
if needle not in text:
    updated = text.replace("    location / {", needle + "\n    location / {", 1)
    if updated == text:
        raise SystemExit("failed to insert nginx include before location /")
    path.write_text(updated)
    print("inserted include")
else:
    print("include already present")
PY
nginx -t
systemctl reload nginx

echo "==> firewall dashboard"
ufw allow 8111/tcp comment "pr-manager dashboard" || true

echo "==> health"
sleep 15
curl -sS -m 10 http://127.0.0.1:8110/health || true
echo
curl -sS -m 10 -o /dev/null -w "https_health:%{http_code}\n" https://hosein.work/pr-manager-api/health || true
curl -sS -m 10 -o /dev/null -w "dashboard:%{http_code}\n" http://127.0.0.1:8111/healthz || true
docker compose -f docker-compose.prod.yml ps
df -h / | tail -1
