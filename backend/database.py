from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.auth.credentials import Credentials
    from google.cloud.firestore_v1.async_client import AsyncClient
    from google.cloud.firestore import Client as SyncClient


@lru_cache(maxsize=1)
def load_firestore_credentials() -> "Credentials | None":
    """Service account from GOOGLE_APPLICATION_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS file path."""
    from google.oauth2 import service_account

    raw = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS_JSON") or "").strip()
    if raw:
        try:
            info = json.loads(raw)
        except json.JSONDecodeError as e:
            raise RuntimeError(
                "GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON. "
                "Paste the full Firebase service account key as one line, or fix escaping in Railway."
            ) from e
        return service_account.Credentials.from_service_account_info(info)

    path_raw = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if not path_raw:
        return None
    p = Path(path_raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parent / path_raw
    if p.is_file():
        return service_account.Credentials.from_service_account_file(str(p))
    return None


def _truthy_env(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def firestore_enabled() -> bool:
    """Use Firestore when project id is set and persistence is not disabled."""
    if _truthy_env("FIRESTORE_DISABLED"):
        return False
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    if not project:
        project = (os.getenv("FIRESTORE_PROJECT_ID") or "").strip()
    return bool(project)


def firestore_project_id() -> str | None:
    project = (os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT") or "").strip()
    if project:
        return project
    return (os.getenv("FIRESTORE_PROJECT_ID") or "").strip() or None


@lru_cache(maxsize=1)
def get_async_firestore() -> "AsyncClient | None":
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud.firestore_v1.async_client import AsyncClient

    if not firestore_enabled():
        return None
    pid = firestore_project_id()
    if not pid:
        return None
    creds = load_firestore_credentials()
    if creds:
        return AsyncClient(project=pid, credentials=creds)
    try:
        return AsyncClient(project=pid)
    except DefaultCredentialsError as e:
        raise RuntimeError(
            "Firestore is enabled (project id is set) but no credentials were found. "
            "In Railway, add GOOGLE_APPLICATION_CREDENTIALS_JSON with the full service account JSON "
            "(Firebase → Project settings → Service accounts → Generate new private key)."
        ) from e


@lru_cache(maxsize=1)
def get_sync_firestore() -> "SyncClient | None":
    from google.auth.exceptions import DefaultCredentialsError
    from google.cloud.firestore import Client as SyncClient

    if not firestore_enabled():
        return None
    pid = firestore_project_id()
    if not pid:
        return None
    creds = load_firestore_credentials()
    if creds:
        return SyncClient(project=pid, credentials=creds)
    try:
        return SyncClient(project=pid)
    except DefaultCredentialsError as e:
        raise RuntimeError(
            "Firestore is enabled but no credentials were found. "
            "Set GOOGLE_APPLICATION_CREDENTIALS_JSON or a valid GOOGLE_APPLICATION_CREDENTIALS file path."
        ) from e


def clear_firestore_caches() -> None:
    load_firestore_credentials.cache_clear()
    get_async_firestore.cache_clear()
    get_sync_firestore.cache_clear()
