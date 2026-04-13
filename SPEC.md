# zog — Zoho CLI (SPEC for Codex)

Build a Python CLI called `zog` that provides Zoho Mail operations from the terminal, modeled after the Google-equivalent CLI `gog` (`/opt/homebrew/bin/gog`). This is the single source of truth. Implement it exactly.

## Philosophy
- Mirror `gog`'s UX and flags. Someone used to `gog` should feel at home.
- Python 3.10+, no heavy framework. Use `argparse` (not click/typer — gog uses flag conventions that argparse handles fine).
- Single package `zog`, installable via `uv tool install .` or `pipx install .`.
- Ship a `zog` console script entrypoint.
- No runtime dependencies beyond Python stdlib + `requests` and `platformdirs`.
- MIT licensed.

## Commands (parity with gog)

```
zog auth add <email> [--services mail]          # OAuth grant-code flow (prints URL, user pastes code)
zog auth list                                    # list stored accounts
zog auth remove <email>                          # remove stored creds

zog mail search -a <email> "<query>" [--max N] [-j|-p]
zog mail get    -a <email> <messageId> [-j|-p]
zog mail thread get -a <email> <threadId> [-j|-p]
zog mail send   -a <email> --to ... --subject ... --body ...
                [--body-file PATH] [--body-html HTML]
                [--cc ...] [--bcc ...]
                [--reply-to-message-id ID]
                [--from EMAIL]                   # if the account has send-as aliases

zog mail folders -a <email> [-j|-p]              # list folders

zog --version
```

## Global flags (on every command)
- `-a, --account EMAIL` — which stored account to use
- `-j, --json` — JSON output
- `-p, --plain` — TSV plain output
- `-v, --verbose` — debug logging
- `-h, --help`

## Output modes
- **Default (pretty table)**: columns aligned with colors when stdout is a TTY.
  For `mail search`: `ID  DATE  FROM  SUBJECT  LABELS  THREAD`
- **JSON (`-j`)**: structured `{status, data, nextPageToken?}` envelope.
- **Plain (`-p`)**: tab-separated values, no colors, stable for scripting.

## Config & storage

```
~/.config/zogcli/
├── config.json                       # {"default_account": "...", "version": 1}
└── keyring/
    └── token/
        └── <email>.json              # {client_id, client_secret, refresh_token, access_token, access_token_expires_at, scopes, org_id?, account_id?, api_url, accounts_url}
```

- File perms: `0700` on dir, `0600` on token files.
- A helper `zog.config` module handles load/save atomically (`os.replace`).
- **Bootstrap**: if `/Users/adebimpeomolaso/.config/zoho/admin-credentials.json` exists on first run and there's no keyring entry yet for `admin@alethiconsulting.com`, import it automatically (a one-time migration), then proceed. Also support a `zog auth import-legacy PATH` command to explicitly import.

## OAuth flow (Zoho Self Client)

For `zog auth add <email>`:
1. Prompt user for Client ID + Client Secret (or read from `ZOHO_CLIENT_ID` / `ZOHO_CLIENT_SECRET` env).
2. Print clear instructions: go to api-console.zoho.com, create/select a Self Client, go to **Generate Code** tab, paste these scopes: `ZohoMail.messages.ALL,ZohoMail.accounts.READ,ZohoMail.folders.READ`, set duration `10 min`, copy the grant code.
3. Read the grant code from stdin (trimmed).
4. POST to `{accounts_url}/oauth/v2/token` with `grant_type=authorization_code` — store refresh_token + scope.
5. Immediately call `GET https://mail.zoho.com/api/accounts` (paginate) and cache the matching `accountId` for the email.
6. Save to `~/.config/zogcli/keyring/token/<email>.json`.

For token refresh: when an API call returns 401 with `INVALID_OAUTHTOKEN`, automatically exchange refresh_token for a new access_token and retry ONCE.

## Zoho Mail API reference (use these endpoints)

Base: `https://mail.zoho.com/api`

- **List accounts**: `GET /accounts` — returns user accounts; pick matching primary email.
- **List folders**: `GET /accounts/{accountId}/folders`
- **Search / list messages in folder**: `GET /accounts/{accountId}/messages/view?folderId={folderId}&limit=10&start=1&searchKey={urlencoded}`
  - `searchKey` supports Zoho's query syntax: `subject:foo from:bar after:YYYYMMDD`. If the user's query doesn't contain `:`, treat it as full-text search on subject+from+body (Zoho handles this natively via `searchKey`).
- **Get single message**: `GET /accounts/{accountId}/folders/{folderId}/messages/{messageId}/content`
  - Alternative header-only: `GET /accounts/{accountId}/folders/{folderId}/messages/{messageId}/header`
- **Send message**: `POST /accounts/{accountId}/messages` with JSON body:
  ```json
  {
    "fromAddress": "admin@alethiconsulting.com",
    "toAddress": "...",
    "ccAddress": "...",
    "bccAddress": "...",
    "subject": "...",
    "content": "...",
    "mailFormat": "html",
    "inReplyTo": "<messageId>",
    "askReceipt": "no"
  }
  ```
- **Thread view**: `GET /accounts/{accountId}/messages/view?threadId={threadId}` — returns all messages in a thread.

Auth header on every call: `Authorization: Zoho-oauthtoken <access_token>`.

## Package layout

```
src/zog/
├── __init__.py            # __version__
├── __main__.py            # python -m zog
├── cli.py                 # argparse wiring, subcommand dispatch
├── config.py              # config/keyring load/save
├── output.py              # pretty/json/plain formatters, TTY detection, colors
├── errors.py              # AuthError, ApiError, ConfigError
├── providers/
│   ├── __init__.py
│   └── zoho/
│       ├── __init__.py
│       ├── auth.py        # oauth exchange + refresh
│       ├── client.py      # requests wrapper with auto-refresh on 401
│       ├── mail.py        # search, get, send, thread, folders
│       └── endpoints.py   # URL builders
└── commands/
    ├── __init__.py
    ├── auth.py
    └── mail.py
```

## Tests

`tests/` — pytest. Include:
- `test_config.py` — roundtrip save/load, perms.
- `test_cli_help.py` — `zog --help`, `zog mail --help` exit 0 with expected text.
- `test_zoho_client_mock.py` — mock `requests.request` and verify `auth refresh on 401 → retry`.
- `test_output_formats.py` — JSON, plain, pretty.
- A **live smoke test** at `tests/smoke_live.py` (not run in CI) that uses the real `admin@alethiconsulting.com` creds in `~/.config/zogcli/keyring/` to fetch the latest 3 messages. Skip if creds not present.

Use `pytest` + `pytest-mock` optionally. No network in CI.

## pyproject.toml

- Name: `zog-cli`
- Version: `0.1.0`
- Python: `>=3.10`
- Deps: `requests>=2.31`, `platformdirs>=4`
- Entry point: `zog = zog.cli:main`
- License: MIT
- Classifiers: Environment :: Console, License :: OSI Approved :: MIT License, etc.

## README.md

Include:
- Badges (MIT license, Python version)
- Install: `pipx install zog-cli` / `uv tool install zog-cli`
- Quickstart: `zog auth add admin@alethiconsulting.com`
- Command reference mirroring gog's style
- Link to Zoho OAuth console
- Contributing section
- Link to LICENSE

## Repo hygiene

- `.gitignore` — Python standard + `.venv`, `__pycache__`, `.pytest_cache`, `dist`, `build`, `*.egg-info`, `.env`, `*.token`.
- `.github/workflows/tests.yml` — run pytest on Python 3.10, 3.11, 3.12 on push/PR to main.
- `CONTRIBUTORS.md` — list Alethi founders.
- `CHANGELOG.md` — 0.1.0 initial release.

## Non-goals (explicitly OUT)
- GoDaddy support — skip.
- Other Zoho services (Calendar/Cliq/WorkDrive) — leave stubs in providers/zoho/ but don't implement.
- Multi-provider plugin system — keep it Zoho-only for now, but structure the code so providers/ can grow.
- Test-mocking network in CI against Zoho itself — mock at the requests layer only.

## Acceptance criteria

After building, these must all pass:

```bash
cd /Users/adebimpeomolaso/Projects/zog
uv venv
source .venv/bin/activate
uv pip install -e .
pytest -q                                              # unit tests pass
zog --version                                          # prints 0.1.0
zog --help                                             # shows all subcommands
zog mail --help                                        # shows search/get/send/folders
zog mail search -a admin@alethiconsulting.com "from:cloudflare" --max 3   # returns real results (uses imported legacy creds)
zog mail send -a admin@alethiconsulting.com --to danieladebimpe@gmail.com --subject "zog test" --body "hello from zog" --dry-run
```

The final test above may be `--dry-run` if implementing a dry-run flag, otherwise skip the live send in acceptance.
