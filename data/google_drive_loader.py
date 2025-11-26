from pathlib import Path
import yaml

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "data" / "data_source.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


@st.cache_resource(show_spinner=False)
def get_drive_service():
    info = dict(st.secrets["gcp_service_account"])
    creds = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/drive.readonly"],
    )
    service = build("drive", "v3", credentials=creds)
    return service


def download_from_drive(file_id: str, dst_path: Path) -> Path:
    service = get_drive_service()

    request = service.files().get_media(fileId=file_id)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    with open(dst_path, "wb") as fh:
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

    return dst_path


def download_operation(force_download: bool = False) -> Path:
    cfg = load_config()["geothermal"]
    file_id = cfg["operation"]

    local_path = PROJECT_ROOT / "data" / "operation.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and not force_download:
        return local_path
    if local_path.exists() and force_download:
        local_path.unlink()

    return download_from_drive(file_id, local_path)


def download_seismic(force_download: bool = False) -> Path:
    cfg = load_config()["geothermal"]
    file_id = cfg["seismic"]

    local_path = PROJECT_ROOT / "data" / "seismic.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists() and not force_download:
        return local_path
    if local_path.exists() and force_download:
        local_path.unlink()

    return download_from_drive(file_id, local_path)
