"""Zoho WorkDrive operations."""

from __future__ import annotations

import os
from typing import Any

from zog.providers.zoho.client import ZohoClient

WORKDRIVE_API_URL = "https://www.zohoapis.com/workdrive/api/v1"


def _endpoint(path: str) -> str:
    return f"{WORKDRIVE_API_URL.rstrip('/')}/{path.lstrip('/')}"


def _wd_headers(extra: dict[str, str] | None = None) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/vnd.api+json"}
    if extra:
        headers.update(extra)
    return headers


def list_files(client: ZohoClient) -> list[dict[str, Any]]:
    """Return files in the root workspace."""

    response = client.get(
        _endpoint("files"),
        headers=_wd_headers({"Content-Type": "application/vnd.api+json"}),
    )
    files = []
    for raw in response.get("data", []) or []:
        files.append(
            {
                "fileId": str(raw.get("id", raw.get("fileId", ""))),
                "name": str(raw.get("attributes", {}).get("name", raw.get("name", ""))),
                "type": str(raw.get("attributes", {}).get("type", raw.get("type", ""))),
                "raw": raw,
            }
        )
    return files


def get_file(client: ZohoClient, file_id: str) -> dict[str, Any]:
    """Fetch a single file by ID."""

    response = client.get(
        _endpoint(f"files/{file_id}"),
        headers=_wd_headers({"Content-Type": "application/vnd.api+json"}),
    )
    raw = response.get("data", {}) or {}
    return {
        "fileId": str(raw.get("id", raw.get("fileId", ""))),
        "name": str(raw.get("attributes", {}).get("name", raw.get("name", ""))),
        "type": str(raw.get("attributes", {}).get("type", raw.get("type", ""))),
        "raw": raw,
    }


def upload_file(
    client: ZohoClient,
    path: str,
    *,
    folder_id: str | None = None,
) -> dict[str, Any]:
    """Upload a file to WorkDrive."""

    if not folder_id:
        raise RuntimeError("WorkDrive upload requires a --folder ID.")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"File not found: {path}")

    filename = os.path.basename(path)
    with open(path, "rb") as f:
        content = f.read()

    response = client.post(
        _endpoint("upload"),
        params={"parent_id": folder_id, "filename": filename},
        data=content,
        headers=_wd_headers({"Content-Type": "application/octet-stream"}),
    )
    files = response.get("data", []) or []
    if files and isinstance(files, list):
        raw = files[0]
    elif isinstance(files, dict):
        raw = files
    else:
        raw = response

    attrs = raw.get("attributes", {}) or raw
    return {
        "fileId": str(attrs.get("resource_id", attrs.get("id", raw.get("id", "")))),
        "name": filename,
        "status": "uploaded",
    }


__all__ = [
    "get_file",
    "list_files",
    "upload_file",
]
