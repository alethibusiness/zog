# zog

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)

`zog` is a Python CLI for Zoho Mail, designed to feel familiar to anyone who already uses `gog` for Google services. It keeps the dependency set small, uses `argparse`, stores credentials under `~/.config/zogcli/`, and supports both machine-readable and terminal-friendly output.

## Install

```bash
pipx install zog-cli
```

```bash
uv tool install zog-cli
```

For local development:

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
```

## Quickstart

Authorize your mailbox:

```bash
zog auth add you@yourdomain.com
```

Search mail:

```bash
zog mail search -a you@yourdomain.com "from:cloudflare" --max 3
```

List folders:

```bash
zog mail folders -a you@yourdomain.com
```

Dry-run a send:

```bash
zog mail send \
  -a you@yourdomain.com \
  --to friend@example.com \
  --subject "zog test" \
  --body "hello from zog" \
  --dry-run
```

### Importing existing Zoho credentials

If you already have a JSON file with `client_id`, `client_secret`, and `refresh_token` from a previous Zoho Self Client setup, you can import it directly:

```bash
zog auth import-legacy /path/to/credentials.json
```

## Command Reference

```text
zog auth add <email> [--services mail]
zog auth list
zog auth remove <email>
zog auth import-legacy <path>

zog mail search -a <email> "<query>" [--max N] [-j|-p]
zog mail get -a <email> <messageId> [-j|-p]
zog mail thread get -a <email> <threadId> [-j|-p]
zog mail send -a <email> --to ... --subject ... --body ...
zog mail folders -a <email> [-j|-p]

zog --version
```

Global flags follow gog-style conventions:

- `-a, --account`
- `-j, --json`
- `-p, --plain`
- `-n, --dry-run`
- `-v, --verbose`
- `-h, --help`

## Output Modes

- Default: aligned table output for list-style commands.
- `--json`: `{"status": "...", "data": ...}` envelope.
- `--plain`: stable TSV for scripting.

## OAuth Setup

`zog auth add` uses Zoho's Self Client flow. Create or select a Self Client in the Zoho API Console:

<https://api-console.zoho.com/>

Use these scopes:

```text
ZohoMail.messages.ALL,ZohoMail.accounts.READ,ZohoMail.folders.READ
```

## Contributing

1. Create a virtual environment with `uv venv`.
2. Install the package in editable mode with `uv pip install -e .[dev]`.
3. Run `pytest -q`.
4. Keep changes small, typed, and focused.

See [LICENSE](LICENSE) for license terms.
