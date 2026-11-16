# Serkan Signage

**Self-hosted digital signage and information dashboard for homes, offices, and shared displays.**

> **Status: Pre-release / source audit in progress.** This repository currently contains project documentation and a Docker packaging scaffold. The real application source is not published yet. **Do not deploy this repository as a working application yet.**

## What it does
Serkan Signage combines a photo slideshow, meal/menu planning, weather information, news and a daily quiz in a TV-friendly dashboard. Designed for a home server and larger display, it uses a lightweight Python HTTP service and can be deployed in Docker.

### Features in the existing private installation
- Photo rotation with locally mounted photo folders; NAS storage can be mounted on the host
- Meal / menu information
- Weather from Open-Meteo
- News from BR24 RSS feeds
- Daily quiz with rotating questions
- Automatic TV display mode
- Password-protected administration
- PWA support and responsive web UI

Some features and sources currently use private configuration and Germany/Bavaria defaults; these need to be made configurable before a public release.

## Planned deployment
```bash
cp .env.example .env
docker compose up -d --build
```
**These commands are illustrative and will not work until the audited `app.py` and validated volume/configuration mapping are added.**

Do not commit `.env`, passwords, session secrets, real user configuration, NAS credentials or photos.

## Documentation
- [Deutsch](README.de.md)
- [Türkçe](README.tr.md)
- [Migration & audit](MIGRATION.md)
- [Security](SECURITY.md)

## License
MIT for the files in this repository. Review any third-party media, feeds, fonts and assets independently before including them.
