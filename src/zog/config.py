"""Config and credential storage helpers."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from zog.errors import ConfigError

APP_NAME = "zogcli"
CONFIG_VERSION = 1
DEFAULT_ACCOUNTS_URL = "https://accounts.zoho.com"
DEFAULT_API_URL = "https://mail.zoho.com"
LEGACY_IMPORT_EMAIL = "admin@alethiconsulting.com"
LEGACY_IMPORT_PATH = Path("/Users/adebimpeomolaso/.config/zoho/admin-credentials.json")


@dataclass(slots=True)
class AppConfig:
    """Top-level CLI config."""

    default_account: str | None = None
    version: int = CONFIG_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "default_account": self.default_account,
            "version": self.version,
        }


@dataclass(slots=True)
class StoredToken:
    """Serialized Zoho credential bundle."""

    client_id: str
    client_secret: str
    refresh_token: str
    access_token: str | None = None
    access_token_expires_at: int | None = None
    scopes: list[str] = field(default_factory=list)
    org_id: str | None = None
    account_id: str | None = None
    api_url: str = DEFAULT_API_URL
    accounts_url: str = DEFAULT_ACCOUNTS_URL

    @classmethod
    def from_mapping(cls, data: dict[str, Any]) -> "StoredToken":
        scopes_value = data.get("scopes") or data.get("scope") or []
        if isinstance(scopes_value, str):
            scopes = [item for item in scopes_value.replace(",", " ").split() if item]
        else:
            scopes = [str(item) for item in scopes_value]
        return cls(
            client_id=str(data["client_id"]),
            client_secret=str(data["client_secret"]),
            refresh_token=str(data["refresh_token"]),
            access_token=data.get("access_token"),
            access_token_expires_at=_optional_int(data.get("access_token_expires_at")),
            scopes=scopes,
            org_id=_optional_str(data.get("org_id")),
            account_id=_optional_str(data.get("account_id")),
            api_url=str(data.get("api_url") or DEFAULT_API_URL),
            accounts_url=str(data.get("accounts_url") or DEFAULT_ACCOUNTS_URL),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
            "access_token": self.access_token,
            "access_token_expires_at": self.access_token_expires_at,
            "scopes": self.scopes,
            "org_id": self.org_id,
            "account_id": self.account_id,
            "api_url": self.api_url,
            "accounts_url": self.accounts_url,
        }


@dataclass(frozen=True, slots=True)
class StoragePaths:
    """Filesystem paths used by zog."""

    config_dir: Path
    keyring_dir: Path
    token_dir: Path
    config_file: Path


def get_storage_paths() -> StoragePaths:
    """Return the configured storage paths."""

    config_root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config_dir = config_root / APP_NAME
    keyring_dir = config_dir / "keyring"
    token_dir = keyring_dir / "token"
    return StoragePaths(
        config_dir=config_dir,
        keyring_dir=keyring_dir,
        token_dir=token_dir,
        config_file=config_dir / "config.json",
    )


def ensure_storage() -> StoragePaths:
    """Create storage directories with secure permissions."""

    paths = get_storage_paths()
    for directory in (paths.config_dir, paths.keyring_dir, paths.token_dir):
        directory.mkdir(parents=True, exist_ok=True)
        os.chmod(directory, 0o700)
    return paths


def load_config() -> AppConfig:
    """Load config, returning defaults if the file is missing."""

    maybe_bootstrap_legacy_import()
    paths = ensure_storage()
    if not paths.config_file.exists():
        return AppConfig()
    try:
        data = json.loads(paths.config_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read config: {exc}") from exc
    return AppConfig(
        default_account=_optional_str(data.get("default_account")),
        version=int(data.get("version", CONFIG_VERSION)),
    )


def save_config(config: AppConfig) -> None:
    """Persist config atomically."""

    paths = ensure_storage()
    _atomic_write_json(paths.config_file, config.to_dict(), mode=0o600)


def token_file(email: str) -> Path:
    """Return the token path for an account."""

    return ensure_storage().token_dir / f"{email}.json"


def list_account_emails() -> list[str]:
    """Return stored account email addresses."""

    maybe_bootstrap_legacy_import()
    token_dir = ensure_storage().token_dir
    emails = [path.stem for path in token_dir.glob("*.json") if path.is_file()]
    return sorted(emails)


def load_account_token(email: str) -> StoredToken:
    """Load stored credentials for an email address."""

    maybe_bootstrap_legacy_import()
    path = token_file(email)
    if not path.exists():
        raise ConfigError(f"No credentials stored for {email}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read token for {email}: {exc}") from exc
    return StoredToken.from_mapping(data)


def save_account_token(email: str, token: StoredToken) -> None:
    """Persist a token file atomically."""

    path = token_file(email)
    _atomic_write_json(path, token.to_dict(), mode=0o600)


def remove_account_token(email: str) -> bool:
    """Delete credentials for an account if present."""

    path = token_file(email)
    if not path.exists():
        return False
    path.unlink()
    config = load_config()
    if config.default_account == email:
        config.default_account = None
        save_config(config)
    return True


def resolve_account(email: str | None) -> str:
    """Resolve the active account from an explicit or default email."""

    if email:
        return email
    config = load_config()
    if config.default_account:
        return config.default_account
    accounts = list_account_emails()
    if len(accounts) == 1:
        return accounts[0]
    if not accounts:
        raise ConfigError("No accounts configured. Run `zog auth add <email>` first.")
    raise ConfigError("Multiple accounts configured. Pass `-a/--account`.")


def set_default_account(email: str) -> None:
    """Update the default account."""

    config = load_config()
    config.default_account = email
    save_config(config)


def import_legacy_credentials(
    path: Path | str,
    *,
    email: str = LEGACY_IMPORT_EMAIL,
    overwrite: bool = True,
    set_default: bool = True,
) -> bool:
    """Import a legacy Zoho credential file into zog storage."""

    legacy_path = Path(path).expanduser()
    if not legacy_path.exists():
        raise ConfigError(f"Legacy credential file not found: {legacy_path}")
    try:
        raw = json.loads(legacy_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Unable to read legacy credentials: {exc}") from exc

    required = {"client_id", "client_secret", "refresh_token"}
    missing = sorted(required - raw.keys())
    if missing:
        raise ConfigError(
            f"Legacy credentials are missing required fields: {', '.join(missing)}"
        )

    target = token_file(email)
    if target.exists() and not overwrite:
        return False

    token = StoredToken.from_mapping(
        {
            "client_id": raw["client_id"],
            "client_secret": raw["client_secret"],
            "refresh_token": raw["refresh_token"],
            "access_token": raw.get("access_token"),
            "access_token_expires_at": raw.get("access_token_expires_at"),
            "scope": raw.get("scope"),
            "scopes": raw.get("scopes"),
            "org_id": raw.get("org_id"),
            "account_id": raw.get("account_id"),
            "api_url": raw.get("api_url", DEFAULT_API_URL),
            "accounts_url": raw.get("accounts_url", DEFAULT_ACCOUNTS_URL),
        }
    )
    save_account_token(email, token)

    if set_default:
        config = load_config()
        if not config.default_account:
            config.default_account = email
            save_config(config)
    return True


def maybe_bootstrap_legacy_import() -> bool:
    """Perform the first-run legacy migration when applicable."""

    if os.environ.get("ZOG_DISABLE_BOOTSTRAP") == "1":
        return False
    target = token_file(LEGACY_IMPORT_EMAIL)
    if target.exists() or not LEGACY_IMPORT_PATH.exists():
        return False
    return import_legacy_credentials(
        LEGACY_IMPORT_PATH,
        email=LEGACY_IMPORT_EMAIL,
        overwrite=False,
        set_default=True,
    )


def _atomic_write_json(path: Path, payload: dict[str, Any], *, mode: int) -> None:
    """Write JSON atomically and set the expected permissions."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        os.chmod(path, mode)
    except OSError as exc:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise ConfigError(f"Unable to write {path}: {exc}") from exc


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _optional_str(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


__all__ = [
    "APP_NAME",
    "AppConfig",
    "CONFIG_VERSION",
    "DEFAULT_ACCOUNTS_URL",
    "DEFAULT_API_URL",
    "LEGACY_IMPORT_EMAIL",
    "LEGACY_IMPORT_PATH",
    "StoragePaths",
    "StoredToken",
    "ensure_storage",
    "get_storage_paths",
    "import_legacy_credentials",
    "list_account_emails",
    "load_account_token",
    "load_config",
    "maybe_bootstrap_legacy_import",
    "remove_account_token",
    "resolve_account",
    "save_account_token",
    "save_config",
    "set_default_account",
    "token_file",
]
