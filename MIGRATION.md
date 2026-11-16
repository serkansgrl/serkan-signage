# Migration from private Serkan Signage installation

The existing application currently runs privately in a Docker container using Python 3.12. The original server must remain untouched during public packaging.

1. Take a **copy** of application source into a separate, private working directory.
2. Inspect source/configuration and replace private NAS mount points and fixed network addresses with documented environment variables.
3. Keep real `config.json`, `secret`, photographs and other runtime data out of version control.
4. Check paths used by the source before finalizing Docker mounts and the internal service port.
5. Validate Python syntax, unit tests and HTTP endpoints in a disposable environment.
6. Verify authentication and browser security headers; confirm the admin path cannot be embedded as an iframe.
7. Run security scanning and review source manually before pushing to a public repository.
8. Release a versioned image only after clean installation succeeds.

**Current status:** documentation and packaging scaffold only; the audited Python source has not been supplied to the repository.
