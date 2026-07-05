# AI Manager

Production-ready, self-hosted control plane for an on-demand AI server.

## Features

- Wake-on-LAN start (`POST /server/start`)
- Readiness detection (ping, SSH, Docker, Ollama, Open WebUI)
- SSH shutdown/restart
- Automatic idle shutdown via APScheduler
- FastAPI REST API + Swagger/OpenAPI
- HTMX + Bootstrap live dashboard
- SQLite history for metrics, activity, audit
- Session-cookie authentication with bcrypt-hashed password
- Prometheus endpoint
- JSON rotating logs with request IDs
- Webhook notifications (Discord, Home Assistant, ntfy)
- Dockerized non-root runtime

## Quick Start

1. Copy environment file:
   ```bash
   cp .env.example .env
   ```
2. Update `.env` values (IP, MAC, SSH key path, URLs, admin hash).
3. Start:
   ```bash
   docker compose up -d --build
   ```
4. Open:
   - Dashboard: `http://<host>:8000/`
   - OpenAPI: `http://<host>:8000/docs`
   - Health: `http://<host>:8000/health`

## API

- `GET /health`
- `GET /status`
- `GET /metrics`
- `GET /history`
- `POST /server/start`
- `POST /server/shutdown`
- `POST /server/restart`
- `POST /keepalive`
- `GET /prometheus`

## Environment

All runtime behavior is configured through `.env`.

### Environment Variable Wiki

| Variable | Default | What it does |
| --- | --- | --- |
| `APP_NAME` | `AI Manager` | Application name shown in UI and OpenAPI metadata. |
| `ENVIRONMENT` | `production` | Runtime environment label used for deployment context. |
| `HOST` | `0.0.0.0` | Bind address for the FastAPI server in container/runtime. |
| `PORT` | `8000` | TCP port exposed by the application server. |
| `SECRET_KEY` | `change-this-secret-key` | Cryptographic key for session cookie signing. Must be unique and secret. |
| `LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, etc.). |
| `LOG_PATH` | `/data/logs/ai-manager.log` | Path to JSON rotating log file. |
| `LOG_MAX_BYTES` | `10485760` | Maximum size of one log file before rotation. |
| `LOG_BACKUP_COUNT` | `5` | Number of rotated log files to keep. |
| `DATABASE_URL` | `sqlite+aiosqlite:////data/ai_manager.db` | SQLAlchemy DSN for persistence (snapshots, events, audit, users). |
| `AI_SERVER_NAME` | `AI Server` | Display name of the managed AI server. |
| `AI_SERVER_IP` | `192.168.1.50` | Target IP used for ping, SSH, and service checks. |
| `AI_SERVER_MAC` | `AA:BB:CC:DD:EE:FF` | MAC address used by Wake-on-LAN magic packets. |
| `SSH_PORT` | `22` | SSH port on the AI server. |
| `SSH_USER` | `aiadmin` | SSH user used for remote control and telemetry commands. |
| `SSH_PRIVATE_KEY` | `/run/secrets/ssh_private_key` | Private key path inside container for SSH authentication. |
| `SSH_KNOWN_HOSTS` | `/data/known_hosts` | Known hosts file used for SSH host key verification. |
| `SSH_TIMEOUT` | `8` | SSH connection/command timeout in seconds. |
| `SSH_SUDO_PASSWORD` | empty | Optional sudo password used when running privileged shutdown command. |
| `OLLAMA_URL` | `http://192.168.1.50:11434` | Ollama base URL used for readiness and model checks. |
| `OPENWEBUI_URL` | `http://192.168.1.50:3000` | Open WebUI base URL used for readiness checks. |
| `PING_TIMEOUT` | `2` | ICMP ping timeout in seconds during health checks. |
| `BOOT_TIMEOUT` | `600` | Max wait time (seconds) before boot timeout notification is triggered. |
| `IDLE_TIMEOUT` | `3600` | Inactivity threshold (seconds) before automatic shutdown. |
| `KEEPALIVE_EXTENSION_SECONDS` | `3600` | Time added to keep-alive window after pressing Keep Alive. |
| `GPU_THRESHOLD` | `10.0` | GPU utilization (%) threshold to classify server as BUSY. |
| `CPU_THRESHOLD` | `10.0` | CPU utilization (%) threshold to classify server as BUSY. |
| `HEALTH_CHECK_INTERVAL_SECONDS` | `20` | Scheduler interval for ping/SSH/Docker/Ollama/Open WebUI checks. |
| `METRICS_INTERVAL_SECONDS` | `60` | Scheduler interval for metrics snapshot collection. |
| `IDLE_CHECK_INTERVAL_SECONDS` | `60` | Scheduler interval for inactivity shutdown evaluation. |
| `DATA_RETENTION_DAYS` | `30` | Number of days to keep snapshot history before cleanup. |
| `PROMETHEUS_ENABLED` | `true` | Enables Prometheus exposition endpoint when true. |
| `PROMETHEUS_PATH` | `/prometheus` | HTTP path where Prometheus metrics are exposed. |
| `ADMIN_USERNAME` | `admin` | Single local administrator username for login. |
| `ADMIN_PASSWORD_HASH` | bcrypt hash | BCrypt password hash for `ADMIN_USERNAME`. |
| `ENERGY_KW_ESTIMATE` | `0.35` | Estimated average power draw (kW) used for energy estimation. |
| `DISCORD_WEBHOOK_URL` | empty | Discord webhook URL for notifications. |
| `HOME_ASSISTANT_WEBHOOK_URL` | empty | Home Assistant webhook URL for notifications. |
| `NTFY_URL` | empty | Base ntfy server URL (for example `https://ntfy.sh`). |
| `NTFY_TOPIC` | empty | ntfy topic name used for push notifications. |
| `ENABLE_TIMELINE` | `true` | Enables timeline page and related dashboard navigation. |
| `ENABLE_DARK_MODE` | `true` | Enables dark mode switch in the UI. |

### Password hash generation

```bash
python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('change-me'))"
```

## SSH Configuration Wiki (AI Server)

This project executes remote commands over SSH for health checks, Docker status, metrics collection, shutdown, and restart.

### 1. Create a dedicated user on the AI server

```bash
sudo adduser --disabled-password --gecos "" aiadmin
sudo usermod -aG docker aiadmin
```

### 2. Generate SSH key pair on the machine running AI Manager

```bash
ssh-keygen -t ed25519 -f ./ssh/ai_manager_key -N ""
```

> Use an **OpenSSH private key** (`-----BEGIN OPENSSH PRIVATE KEY-----`).
> PuTTY `.ppk` files are not accepted directly by this service.
> Convert `.ppk` to OpenSSH with PuTTYgen if needed.

### 3. Install the public key on the AI server

```bash
sudo -u aiadmin mkdir -p /home/aiadmin/.ssh
sudo -u aiadmin chmod 700 /home/aiadmin/.ssh
sudo -u aiadmin tee -a /home/aiadmin/.ssh/authorized_keys < ./ssh/ai_manager_key.pub
sudo -u aiadmin chmod 600 /home/aiadmin/.ssh/authorized_keys
```

### 4. Allow controlled shutdown without interactive password

```bash
echo 'aiadmin ALL=(root) NOPASSWD:/sbin/shutdown,/usr/sbin/shutdown' | sudo tee /etc/sudoers.d/ai-manager
sudo chmod 440 /etc/sudoers.d/ai-manager
```

### 5. Validate SSH connectivity from AI Manager host

```bash
ssh -i ./ssh/ai_manager_key aiadmin@192.168.1.42 "echo ok"
ssh -i ./ssh/ai_manager_key aiadmin@192.168.1.42 "docker ps --format '{{.Names}}' | head -n 5"
ssh -i ./ssh/ai_manager_key aiadmin@192.168.1.42 "sudo shutdown -k now"
```

### 6. Configure `.env`

```env
SSH_USER=aiadmin
SSH_PORT=22
SSH_PRIVATE_KEY=/run/secrets/ssh_private_key
SSH_KNOWN_HOSTS=/data/known_hosts
SSH_TIMEOUT=8
SSH_SUDO_PASSWORD=
```

### 7. Mount the private key into the container

In `docker-compose.yml`, map your key into `/run/secrets/ssh_private_key` (already expected by `.env.example`):

```yaml
volumes:
  - ./ssh:/run/secrets:ro
```

Place the key at:

```text
./ssh/ssh_private_key
```

Or change `SSH_PRIVATE_KEY` to match your filename.

### 8. Common SSH troubleshooting

- `FileNotFoundError: /run/secrets/ssh_private_key`: the key file is not mounted at the configured path.
- `Invalid SSH private key format`: key is likely `.ppk`; convert it to OpenSSH format and update `SSH_PRIVATE_KEY`.
- `Permission denied (publickey)`: key/user mismatch or `authorized_keys` permissions are wrong.
- `sudo: a password is required`: sudoers NOPASSWD is missing for `shutdown`.
- `Docker DOWN while server is up`: user is not in `docker` group on AI server.
- `Host key verification issues`: add server host key to `SSH_KNOWN_HOSTS`.

### 9. Windows path examples for `.env`

If you run AI Manager directly on Windows (not Docker), use either:

```env
SSH_PRIVATE_KEY=\\\\TRUENAS\\system\\system\\clersa\\ai_manager_key
```

or:

```env
SSH_PRIVATE_KEY=//TRUENAS/system/system/clersa/ai_manager_key
```

Avoid quoted values with single backslashes and avoid `.ppk` as the configured key.

## Local Development

```bash
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```
```bash
pip install -r requirements.txt
```
```bash
uvicorn app.main:app --reload
```
```bash
pytest -q
```
