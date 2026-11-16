# Serkan Signage

**Self-hosted digital signage dashboard — photos, meal planner, weather, news and a daily quiz.**

**Languages:** [English](README.md) · [Deutsch](README.de.md) · [Türkçe](README.tr.md)

Serkan Signage is an independent lightweight Python application for a home server, NAS or office information display. It offers a responsive dashboard, a fullscreen/TV presentation mode, a photo slideshow, a weekly menu, 7-day weather, RSS news and five daily multiple-choice questions. It also has a password-protected administration page and installable PWA support.

## Features

- **Photo slideshow:** upload images from the admin page or mount an existing NAS photo directory (read-only).
- **Weekly meals:** manage seven meal entries from the admin panel.
- **Weather:** Open-Meteo seven-day forecast; configure city/coordinates in the admin panel. Optional browser geolocation requires HTTPS.
- **News:** BR24 RSS defaults; RSS URLs and approved article domains can be configured.
- **Daily quiz:** five German-language questions, rotated automatically.
- **TV mode:** news and quiz alternate automatically, with correct quiz answers revealed near the end of each question.
- **Admin & PWA:** admin at `/serkan`, fullscreen button, home-screen installation.

The supplied UI and quiz are currently **German-language**. The README is translated into three languages; the UI itself is not yet translated.

## Requirements

- Docker Engine and Docker Compose plugin
- A free unused TCP port (default `8098` on localhost)
- Internet access for Open-Meteo and RSS feeds (otherwise the page can still load)
- Optionally, a host-mounted directory of photos

## Quick start

```sh
git clone https://github.com/serkansgrl/serkan-signage.git
cd serkan-signage
cp .env.example .env
```

**Edit `.env` first:** Replace `REPLACE_WITH_A_STRONG_UNIQUE_PASSWORD` with your own password of at least 12 characters.

```sh
docker compose up -d --build
docker compose ps
```

Open `http://127.0.0.1:8098/` **on the Docker host**, or access via an SSH tunnel. Administration: `http://127.0.0.1:8098/serkan`.

The default bind address is `127.0.0.1` for security, so the display will **not** be reachable directly from other LAN devices. For trusted LAN access, set `BIND_ADDRESS=0.0.0.0` in `.env` and restrict access with the host firewall. For internet exposure, use HTTPS behind a reverse proxy and set `COOKIE_SECURE=true`; consider additional access protection for `/serkan`.

**Password behavior:** `INITIAL_ADMIN_PASSWORD` creates the initial password hash only on the first startup with an empty data volume. It does not reset the password on later starts. You can change the admin password from the admin panel.

## Photo storage

Local uploaded photos, application config, secret key and password hash live in the named Docker volume `signage_data`. Back up this volume privately.

To display photos from your own NAS, first mount the NAS share on the Docker host using an appropriate protocol (prefer SMB3/NFS). Set `NAS_PHOTOS_PATH` in `.env` to the **host directory**. It is mounted read-only at `/nas-photos` inside the container.

Supported photos: JPEG, PNG, GIF and WebP. Avoid granting the container access to your whole NAS. The application does not configure SMB, NFS or NAS credentials itself.

## Settings (.env)

| Name | Description | Default |
| --- | --- | --- |
| `INITIAL_ADMIN_PASSWORD` | Mandatory first-run password, minimum 12 characters | Must be changed |
| `BIND_ADDRESS` | Host network bind | `127.0.0.1` |
| `HTTP_PORT` | Host-side TCP port | `8098` |
| `TZ` | Timezone for weather/quiz | `Europe/Berlin` |
| `COOKIE_SECURE` | Secure admin cookies on HTTPS | `false` |
| `FRAME_ANCESTORS` | Optional allowed origin(s) for embedding **only** the public home screen | Empty (iframe blocked) |
| `NAS_PHOTOS_PATH` | Host photo folder | `./examples/nas-photos` |
| `NEWS_FEEDS` | Comma-separated HTTPS RSS feed URLs | BR24 |
| `NEWS_ALLOWED_HOSTS` | Comma-separated allowed HTTPS news article hostnames | `www.br.de,br.de` |
| `NEWS_SOURCE_LABEL` | Source name in JSON API | `BR24` |

For `FRAME_ANCESTORS`, use explicit origins such as `https://signage.example.org` (no trailing path). The admin area always sends `X-Frame-Options: DENY`.

## Endpoints

- `/` display
- `/serkan` admin/login
- `/health` health check
- `/api/state` public display state
- `/api/extras` public news and quiz
- `/pwa/manifest.webmanifest` PWA metadata

The display, its photos and public APIs are **not private**. Only admin changes are protected by login. Keep personal photos or menus off a publicly reachable deployment.

## Tests and updates

```sh
python3 -m unittest discover -s tests -v
docker compose config
docker compose build
docker compose up -d
```

The CI checks Python/HTTP smoke tests, Compose configuration and Docker builds. Watch the [Actions tab](https://github.com/serkansgrl/serkan-signage/actions) for the latest result. A passing test is not a full external security audit.

## More

- [Security and responsible disclosure](SECURITY.md)
- [Migration notes](MIGRATION.md)
- [MIT License](LICENSE)

News summaries and linked articles belong to their respective publishers; the MIT license does not cover third-party content or media.
