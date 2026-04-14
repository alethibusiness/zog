# Changelog

## 0.3.1 - 2026-04-14

- Fix: loopback callback now uses `http://127.0.0.1:<port>/callback` instead of `http://localhost:<port>/callback`. On systems where `localhost` resolves to IPv6 first, the browser could hit an unrelated process on the same port and receive a 404. Using the IPv4 literal avoids that entirely.

## 0.3.0 - 2026-04-14

- Replaced Self Client flow with OAuth 2.0 Authorization Code flow (local loopback by default, OOB fallback).
- `zog auth add` opens a browser and waits for the authorization callback on localhost — no manual code entry needed.
- `--no-browser` / `--oob` prints the URL and prompts for the code (for SSH / headless environments).
- `--self-client` preserves the original flow for power users who want their own Zoho app.
- Refreshing tokens now uses the embedded client credentials by default.
- Removed the experimental device_flow module (Zoho doesn't implement RFC 8628).

## 0.2.2 - 2026-04-13

- Fix Zoho Calendar/Contacts/WorkDrive endpoints; live-tested against admin@alethiconsulting.com.

## 0.2.1 - 2026-04-13

- Moved repository to `Alethi-Consulting` GitHub organization.
- Updated project URLs in packaging metadata.

## 0.2.0 - 2026-04-13

- Added `zog calendar` subcommands: `list`, `events list`, `events get`, `events create`.
- Added `zog contacts` subcommands: `list`, `get`, `create`.
- Added `zog workdrive` subcommands: `files list`, `files get`, `upload` (stub).
- Expanded default OAuth scopes to cover Mail, Calendar, Contacts, and WorkDrive.
- Added `--services` CSV flag to `zog auth add` for scoped authorization.
- Added mock-based tests for Calendar, Contacts, and WorkDrive providers.

## 0.1.0 - 2026-04-13

- Initial release of `zog`.
- Added gog-style CLI commands for Zoho Mail auth, search, get, thread get, send, and folders.
- Added local credential storage, legacy credential auto-import, JSON/plain/pretty output, tests, and CI.
