"""Zoho WorkDrive operations."""

from __future__ import annotations

from typing import Any

from zog.providers.zoho.client import ZohoClient

WORKDRIVE_API_URL = "https://workdrive.zoho.com/api/v1"


def _endpoint(path: str) -> str:
    return f"{WORKDRIVE_API_URL.rstrip('/')}/{path.lstrip('/')}"


def list_files(client: ZohoClient) -> list[dict[str, Any]]:
    """Return files in the root workspace."""

    response = client.get(_endpoint("files"))
    files = []
    for raw in response.get("data", []) or []:
        files.append(
            {
                "fileId": str(raw.get("id", raw.get("fileId", ""))),
                "name": str(raw.get("name", "")),
                "type": str(raw.get("type", "")),
                "raw": raw,
            }
        )
    return files


def get_file(client: ZohoClient, file_id: str) -> dict[str, Any]:
    """Fetch a single file by ID."""

    response = client.get(_endpoint(f"files/{file_id}"))
    raw = response.get("data", {}) or {}
    return {
        "fileId": str(raw.get("id", raw.get("fileId", ""))),
        "name": str(raw.get("name", "")),
        "type": str(raw.get("type", "")),
        "raw": raw,
    }


def upload_file(
    client: ZohoClient,
    path: str,
    *,
    folder_id: str | None = None,
) -> dict[str, Any]:
    """Upload a file to WorkDrive."""

    raise NotImplementedError(
        "WorkDrive upload is not yet implemented. "
        "Use the Zoho WorkDrive web UI or API directly."
    )


__all__ = [
    "get_file",
    "list_files",
    "upload_file",
]
