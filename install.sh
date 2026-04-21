#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
DEFAULT_USER="${SUDO_USER:-${USER:-ubuntu}}"
DEFAULT_PORT="8000"
DEFAULT_GEOLOOKUP_URL="https://ipwho.is"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=""
else
  SUDO="sudo"
fi

print_step() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

prompt_value() {
  local prompt_text="$1"
  local default_value="${2:-}"
  local entered_value

  if [[ -n "$default_value" ]]; then
    read -r -p "$prompt_text [$default_value]: " entered_value
    printf '%s' "${entered_value:-$default_value}"
  else
    read -r -p "$prompt_text: " entered_value
    printf '%s' "$entered_value"
  fi
}

prompt_secret() {
  local prompt_text="$1"
  local entered_value=""
  while [[ -z "$entered_value" ]]; do
    read -r -s -p "$prompt_text: " entered_value
    printf '\n'
  done
  printf '%s' "$entered_value"
}

confirm() {
  local prompt_text="$1"
  local default_answer="${2:-Y}"
  local answer=""
  read -r -p "$prompt_text [$default_answer/n]: " answer || true
  answer="${answer:-$default_answer}"
  [[ "$answer" =~ ^[Yy]$ ]]
}

ensure_ubuntu() {
  if [[ ! -f /etc/os-release ]]; then
    echo "Could not detect the operating system."
    exit 1
  fi

  if ! grep -q 'Ubuntu' /etc/os-release; then
    echo "This installer is prepared for Ubuntu 22.04 and similar Ubuntu systems."
    exit 1
  fi
}

require_command() {
  local name="$1"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "Required command '$name' is missing."
    exit 1
  fi
}

extract_host() {
  local url="$1"
  url="${url#http://}"
  url="${url#https://}"
  url="${url%%/*}"
  url="${url%%:*}"
  printf '%s' "$url"
}

is_ip_address() {
  local host="$1"
  [[ "$host" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]
}

write_env_file() {
  local bot_token="$1"
  local public_webapp_url="$2"
  local app_port="$3"
  local geolookup_url="$4"

  cat > "$APP_DIR/.env" <<EOF
BOT_TOKEN=$bot_token
PUBLIC_WEBAPP_URL=$public_webapp_url
HOST=127.0.0.1
PORT=$app_port
DB_PATH=$APP_DIR/data/nettool.db
GEOLOOKUP_URL=$geolookup_url
EOF
  chmod 600 "$APP_DIR/.env"
}

prepare_permissions() {
  local app_user="$1"
  mkdir -p "$APP_DIR/data"

  if id "$app_user" >/dev/null 2>&1; then
    $SUDO chown "$app_user":"$app_user" "$APP_DIR/.env"
    $SUDO chown -R "$app_user":"$app_user" "$APP_DIR/data"
  fi
}

render_template() {
  local source_file="$1"
  local target_file="$2"
  local app_user="$3"
  local app_port="$4"
  local server_name="$5"

  sed \
    -e "s|__APP_DIR__|$APP_DIR|g" \
    -e "s|__APP_USER__|$app_user|g" \
    -e "s|__APP_PORT__|$app_port|g" \
    -e "s|__SERVER_NAME__|$server_name|g" \
    "$source_file" > "$target_file"
}

install_packages() {
  print_step "Installing Ubuntu packages"
  $SUDO apt update
  $SUDO apt install -y \
    python3 \
    python3-venv \
    python3-pip \
    traceroute \
    iputils-ping \
    nginx \
    certbot \
    python3-certbot-nginx
}

setup_python() {
  print_step "Creating virtual environment"
  python3 -m venv "$APP_DIR/.venv"
  "$APP_DIR/.venv/bin/pip" install --upgrade pip
  "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt"
}

install_systemd_units() {
  local app_user="$1"

  print_step "Installing systemd services"
  render_template \
    "$APP_DIR/deploy/systemd/nettool-api.service.template" \
    "/tmp/nettool-api.service" \
    "$app_user" \
    "$APP_PORT" \
    "$SERVER_NAME"
  render_template \
    "$APP_DIR/deploy/systemd/nettool-bot.service.template" \
    "/tmp/nettool-bot.service" \
    "$app_user" \
    "$APP_PORT" \
    "$SERVER_NAME"

  $SUDO cp /tmp/nettool-api.service /etc/systemd/system/nettool-api.service
  $SUDO cp /tmp/nettool-bot.service /etc/systemd/system/nettool-bot.service
  $SUDO systemctl daemon-reload
  $SUDO systemctl enable nettool-api.service
  $SUDO systemctl enable nettool-bot.service
}

install_nginx_config() {
  print_step "Installing nginx site"
  render_template \
    "$APP_DIR/deploy/nginx/nettool.conf.template" \
    "/tmp/nettool-nginx.conf" \
    "$APP_USER" \
    "$APP_PORT" \
    "$SERVER_NAME"

  $SUDO cp /tmp/nettool-nginx.conf /etc/nginx/sites-available/nettool
  $SUDO ln -sf /etc/nginx/sites-available/nettool /etc/nginx/sites-enabled/nettool
  if [[ -f /etc/nginx/sites-enabled/default ]]; then
    $SUDO rm -f /etc/nginx/sites-enabled/default
  fi
  $SUDO nginx -t
  $SUDO systemctl enable nginx
  $SUDO systemctl restart nginx
}

obtain_certificate() {
  if is_ip_address "$SERVER_NAME"; then
    print_step "Skipping Let's Encrypt because PUBLIC_WEBAPP_URL uses an IP address"
    return
  fi

  if confirm "Request and install a Let's Encrypt certificate for $SERVER_NAME?" "Y"; then
    print_step "Requesting Let's Encrypt certificate"
    $SUDO certbot --nginx -d "$SERVER_NAME"
  else
    print_step "Skipping Let's Encrypt certificate setup"
  fi
}

start_services() {
  print_step "Starting services"
  $SUDO systemctl restart nettool-api.service
  $SUDO systemctl restart nettool-bot.service
}

show_summary() {
  print_step "Installation complete"
  cat <<EOF
NetTool is installed.

Project directory: $APP_DIR
Public URL: $PUBLIC_WEBAPP_URL

Useful commands:
  sudo systemctl status nettool-api.service
  sudo systemctl status nettool-bot.service
  sudo journalctl -u nettool-api.service -f
  sudo journalctl -u nettool-bot.service -f
  curl http://127.0.0.1:$APP_PORT/healthz

Next step in BotFather:
  Open your bot settings and make sure the Web App button points to:
  $PUBLIC_WEBAPP_URL
EOF
}

ensure_ubuntu
require_command python3
require_command sed

print_step "NetTool turnkey installer"
BOT_TOKEN="$(prompt_secret 'Enter Telegram bot token')"
PUBLIC_WEBAPP_URL="$(prompt_value 'Enter public HTTPS URL for the Web App' 'https://example.com')"
APP_USER="$(prompt_value 'Enter Linux user that should run the services' "$DEFAULT_USER")"
APP_PORT="$(prompt_value 'Enter internal API port' "$DEFAULT_PORT")"
GEOLOOKUP_URL="$(prompt_value 'Enter geolocation provider URL' "$DEFAULT_GEOLOOKUP_URL")"
SERVER_NAME="$(extract_host "$PUBLIC_WEBAPP_URL")"

if [[ "$PUBLIC_WEBAPP_URL" != https://* ]]; then
  echo "PUBLIC_WEBAPP_URL must start with https:// for Telegram Web Apps."
  exit 1
fi

write_env_file "$BOT_TOKEN" "$PUBLIC_WEBAPP_URL" "$APP_PORT" "$GEOLOOKUP_URL"
install_packages
setup_python
prepare_permissions "$APP_USER"
install_systemd_units "$APP_USER"
install_nginx_config
obtain_certificate
start_services
show_summary
