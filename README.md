# NetTool Telegram Bot

Telegram bot with a Web App for network diagnostics:

- Ping
- Traceroute
- IP geolocation
- TCP port availability check
- Per-user favorite servers

Stack:

- Python
- FastAPI
- aiogram
- SQLite
- Telegram Web App

## Turnkey install on Ubuntu 22.04

There is now an installer script that prepares the server end-to-end:

```bash
chmod +x install.sh
./install.sh
```

What it does:

- installs Ubuntu packages
- creates `.venv`
- installs Python requirements
- asks for your bot token
- asks for the public Web App URL
- writes `.env`
- installs `systemd` units
- installs `nginx` config
- optionally requests a Let's Encrypt certificate

The installer expects:

- Ubuntu 22.04 or a similar Ubuntu server
- a public domain or HTTPS endpoint for Telegram Web App
- DNS already pointed to the server if you want automatic TLS

## Project layout

- `app/main.py` - FastAPI app and API routes
- `app/services/network_tools.py` - ping, traceroute, DNS resolve, port checks
- `app/services/geolocation.py` - external IP geolocation lookup
- `app/security.py` - Telegram Web App `initData` validation
- `bot.py` - Telegram bot with button that opens the Web App
- `static/` - frontend for Telegram Mini App

## Quick start

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Prepare environment:

```bash
cp .env.example .env
```

Fill in:

- `BOT_TOKEN` - your bot token from BotFather
- `PUBLIC_WEBAPP_URL` - public HTTPS URL of the web app

4. Run the API:

```bash
python3 run.py
```

5. In another terminal, run the bot:

```bash
python3 bot.py
```

## Ubuntu 22.04 notes

Install system packages:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip traceroute iputils-ping
```

The bot Web App URL must be public and served over HTTPS. A typical production setup is:

- FastAPI behind `nginx`
- TLS via `certbot`
- two `systemd` services: one for `run.py`, one for `bot.py`

Ready-made templates are included in:

- `deploy/systemd/nettool-api.service.template`
- `deploy/systemd/nettool-bot.service.template`
- `deploy/nginx/nettool.conf.template`

## Example systemd service for API

```ini
[Unit]
Description=NetTool API
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/nettool
EnvironmentFile=/opt/nettool/.env
ExecStart=/opt/nettool/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Example systemd service for bot

```ini
[Unit]
Description=NetTool Telegram Bot
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/opt/nettool
EnvironmentFile=/opt/nettool/.env
ExecStart=/opt/nettool/.venv/bin/python bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

## Important implementation notes

- Favorites are bound to Telegram users by validated `initData`.
- Geolocation uses `ipwho.is` by default and can be changed via `GEOLOOKUP_URL`.
- `traceroute` requires the system package to be installed on the server.
- Port checks use TCP connect and report whether the port accepted the connection.

## Next good steps

- Add webhook mode for the bot instead of polling.
- Add history of executed checks.
- Add rate limiting per user.
- Protect API with reverse proxy limits and logging.
