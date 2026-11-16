# Migration and compatibility

This repository contains the **general-purpose Serkan Signage code**. It is separate from the maintainer's original private installation.

## Fresh installation

1. Clone the repository and copy `.env.example` to `.env`.
2. Set a unique password in `INITIAL_ADMIN_PASSWORD` (12+ characters).
3. Configure local network access and optional `NAS_PHOTOS_PATH`.
4. Run `docker compose up -d --build`.
5. Open the dashboard; sign into `/serkan` to update meal items, location and add photos.

## Upgrading

- Back up your `signage_data` volume before upgrading.
- `config.json`, `secret`, `password.json` and uploaded images must remain together in the **same persistent Docker volume**.
- The initial password environment variable is used only at first startup when `password.json` does not yet exist.
- Do not copy data, credentials or NAS mount configuration from another person's server.
- This public project does not automatically migrate old external Nginx / Cloudflare / LibreSignage configurations.
- For reverse-proxy deployments, use HTTPS with `COOKIE_SECURE=true`; if you use iframe embeds, configure `FRAME_ANCESTORS` with explicit trusted origins.

## Validation

```sh
python3 -m unittest discover -s tests -v
docker compose config
docker compose build
```

GitHub Actions runs Python, HTTP and Docker build checks for incoming changes. Production security and data backup remain the deployment administrator's responsibility.
