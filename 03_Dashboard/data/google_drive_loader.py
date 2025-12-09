# 03_Dashboard/data/google_drive_loader.py

from pathlib import Path
import json
import yaml

import streamlit as st
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

# PROJECT_ROOT = folder 03_Dashboard
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "data" / "data_source.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


@st.cache_resource(show_spinner=False)
def get_authed_session() -> AuthorizedSession:
    """
    Create an AuthorizedSession using:
    - LOCAL: service account JSON file (03_Dashboard/geothermal_secret/lateral-faculty-479223-b3-398fb870e3f2.json)
    - CLOUD: st.secrets["gcp_service_account"]
    """
    # 1) LOCAL: service account JSON file
    sa_path = PROJECT_ROOT / "geothermal_secret" / "service_account.json"

    if sa_path.exists():
        # Local dev: read JSON from file
        with open(sa_path, "r") as f:
            info = json.load(f)
    else:
        # 2) CLOUD: use Streamlit secrets
        if "gcp_service_account" not in st.secrets:
            raise RuntimeError(
                "No local service_account.json found and 'gcp_service_account' is "
                "missing in st.secrets. Please configure one of them."
            )
        info = dict(st.secrets["gcp_service_account"])

    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    session = AuthorizedSession(creds)
    return session


def download_from_drive(file_id: str, dst_path: Path) -> Path:
    """
    Download a file from Google Drive (by file_id) to dst_path
    using a simple HTTPS GET with an AuthorizedSession.
    """
    session = get_authed_session()

    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media"
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    with session.get(url, stream=True) as resp:
        resp.raise_for_status()
        with open(dst_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1 MB
                if chunk:
                    f.write(chunk)

    return dst_path


def download_operation(force_download: bool = False) -> Path:
    cfg = load_config()["geothermal"]
    file_id = cfg["operation"]

    local_path = PROJECT_ROOT / "data" / "operation.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and local_path.stat().st_size > 0 and not force_download:
        return local_path

    if local_path.exists():
        local_path.unlink()

    return download_from_drive(file_id, local_path)


def download_seismic(force_download: bool = False) -> Path:
    cfg = load_config()["geothermal"]
    file_id = cfg["seismic"]

    local_path = PROJECT_ROOT / "data" / "seismic.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and local_path.stat().st_size > 0 and not force_download:
        return local_path

    if local_path.exists():
        local_path.unlink()

    return download_from_drive(file_id, local_path)


if __name__ == "__main__":
    op_path = download_operation(force_download=True)
    sei_path = download_seismic(force_download=True)
    print("Operation downloaded to:", op_path)
    print("Seismic   downloaded to:", sei_path)
