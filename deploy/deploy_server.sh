#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/www/wwwroot/guidance"
ARCHIVE_PATH="${1:-/tmp/guidance-deploy.tar.gz}"
DOMAIN="guidance.csgozbt.com"

if [[ ! -f "$ARCHIVE_PATH" ]]; then
  echo "Deploy archive not found: $ARCHIVE_PATH" >&2
  exit 1
fi

if [[ -z "${AMAP_API_KEY:-}" ]]; then
  echo "AMAP_API_KEY is required in environment." >&2
  exit 1
fi

mkdir -p "$APP_DIR" /www/wwwlogs
rm -rf "$APP_DIR/backend" "$APP_DIR/frontend"
tar -xzf "$ARCHIVE_PATH" -C "$APP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y python3 python3-venv python3-pip
  elif command -v yum >/dev/null 2>&1; then
    yum install -y python3 python3-pip
  else
    echo "python3 is missing and no supported package manager was found." >&2
    exit 1
  fi
fi

python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/backend/requirements.txt"

cat > "$APP_DIR/backend/.env" <<EOF
APP_ENV=production
APP_NAME=store-advisor
API_HOST=127.0.0.1
API_PORT=8000
AMAP_API_KEY=${AMAP_API_KEY}
DEFAULT_SEARCH_RADIUS_METERS=1000
LLM_PROVIDER=qwen
LLM_API_KEY=
LLM_MODEL=qwen-plus
DATABASE_URL=${DATABASE_URL:-sqlite:///./store_advisor.db}
EOF
chmod 600 "$APP_DIR/backend/.env"

cat > /etc/systemd/system/guidance-api.service <<'EOF'
[Unit]
Description=Store Opening Guidance FastAPI service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/www/wwwroot/guidance/backend
EnvironmentFile=/www/wwwroot/guidance/backend/.env
ExecStart=/www/wwwroot/guidance/venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable guidance-api
systemctl restart guidance-api

NGINX_CONF="/www/server/panel/vhost/nginx/${DOMAIN}.conf"
if [[ ! -d "/www/server/panel/vhost/nginx" ]]; then
  NGINX_CONF="/etc/nginx/conf.d/${DOMAIN}.conf"
fi

mkdir -p "$(dirname "$NGINX_CONF")"
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name ${DOMAIN} 165.154.40.121;

    root ${APP_DIR}/frontend;
    index index.html;

    access_log /www/wwwlogs/guidance.access.log;
    error_log /www/wwwlogs/guidance.error.log;

    client_max_body_size 20m;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }
}
EOF

if [[ -x "/www/server/nginx/sbin/nginx" ]]; then
  /www/server/nginx/sbin/nginx -t
  /www/server/nginx/sbin/nginx -s reload
else
  nginx -t
  systemctl reload nginx || systemctl restart nginx
fi

if command -v firewall-cmd >/dev/null 2>&1; then
  firewall-cmd --add-service=http --permanent || true
  firewall-cmd --add-service=https --permanent || true
  firewall-cmd --reload || true
fi

if command -v ufw >/dev/null 2>&1; then
  ufw allow 80/tcp || true
  ufw allow 443/tcp || true
fi

curl -fsS http://127.0.0.1:8000/api/health
echo
echo "Deployment completed: http://${DOMAIN}/"
