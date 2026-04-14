# Changelog

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
