# Serkan Signage — Security Policy

The software is a self-hosted application intended primarily for trusted home and office networks. **A passing CI build or smoke test is not an independent security audit.**

## Exposure

- The dashboard (`/`), photos (`/photo/...`) and JSON APIs (`/api/state`, `/api/extras`) are accessible without login.
- The administrator endpoint (`/serkan`) requires authentication; modifying operations also check a CSRF token.
- Treat `.env`, Docker volume `signage_data`, `secret`, `password.json` and private photos as sensitive. Never put live copies in Git history.
- Default Docker binding is localhost. Restrict access with firewall rules or put a reverse proxy in front.
- For public HTTPS deployment, configure `COOKIE_SECURE=true`; enable access restrictions for `/serkan` (VPN, SSO, access proxy).
- The dashboard rejects framing unless you explicitly set `FRAME_ANCESTORS`. The admin panel always sends `X-Frame-Options: DENY`.
- The initial admin password must be unique and at least 12 characters.
- Use host-mounted NAS shares in read-only mode; do not store NAS credentials inside the app.
- Keep your Docker host and base image patched; avoid mounting the Docker socket in the app.

## Reporting security issues

Report suspected issues privately to the repository owner. Do not include actual passwords, tokens, private photos or NAS credentials in public issues.

## Scope limitations

No formal penetration test has been performed. Rate limiting and sessions are lightweight and designed for small self-hosted deployments; do not rely on application authentication alone for unrestricted internet exposure.
