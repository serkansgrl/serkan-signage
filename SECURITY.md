# Security Policy

**This repository is a pre-release scaffold and has not been audited for production deployment.**

Never commit private configuration, `.env`, runtime secrets, API keys, passwords, cookie/session keys, private photos or NAS mount credentials. Treat even a private GitHub repository as an inappropriate place for unencrypted live secrets.

Before publication:
1. Audit the exact deployed Python source and its dependencies.
2. Remove hard-coded local paths, IP addresses and personal data.
3. Verify all endpoint authentication, CSRF protection and session cookie settings.
4. Secure the administrator interface with HTTPS and preferably an additional access-control layer.
5. Review CORS and framing headers; enable embedding only for explicitly trusted origins.
6. Test with fresh empty data volumes and clean Docker installation.
7. Check for exposed secrets in Git history, not only in current files.

Report security issues privately to the repository owner rather than opening a public issue with exploit details.
