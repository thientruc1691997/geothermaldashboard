from pathlib import Path

from dotenv import load_dotenv
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import yaml

# google_drive_loader.py nằm ở: ROOT / data / google_drive_loader.py
PROJECT_ROOT = Path(__file__).resolve().parent.parent

ENV_PATH = PROJECT_ROOT / ".env"
SETTINGS_PATH = PROJECT_ROOT / "setting.yaml"              # file cấu hình PyDrive2
CONFIG_PATH = PROJECT_ROOT / "data" / "data_source.yaml"   # chứa id file Drive


def load_config():
    """Đọc file data_source.yaml và trả về dict."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_drive() -> GoogleDrive:
    """
    Khởi tạo GoogleDrive với config từ .env và setting.yaml.
    Lần đầu chạy sẽ mở browser để login, sau đó cache credential.
    """
    load_dotenv(ENV_PATH)

    gauth = GoogleAuth(settings_file=str(SETTINGS_PATH))
    gauth.LocalWebserverAuth()  # lần đầu sẽ mở browser để login
    drive = GoogleDrive(gauth)
    return drive


def download_from_drive(file_id: str, dst_path: Path) -> Path:
    """
    Tải 1 file từ Google Drive về đúng đường dẫn dst_path.
    Luôn overwrite nếu file đã tồn tại.
    """
    dst_path = Path(dst_path)
    dst_path.parent.mkdir(parents=True, exist_ok=True)

    drive = get_drive()
    gfile = drive.CreateFile({"id": file_id})
    gfile.GetContentFile(str(dst_path))

    return dst_path


def download_operation(force_download: bool = False) -> Path:
    """
    Trả về path tới file data/operation.csv.

    - Chỉ tải từ Drive nếu:
        + file chưa tồn tại, hoặc
        + force_download = True
    - Luôn giữ đúng tên: operation.csv (không tạo 'operation 2.csv').
    """
    cfg = load_config()["geothermal"]
    file_id = cfg["operation"]

    local_path = PROJECT_ROOT / "data" / "operation.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists():
        if not force_download:
            return local_path
        # muốn tải lại thì xoá file cũ để chắc chắn không sinh thêm operation 2.csv
        local_path.unlink()

    download_from_drive(file_id=file_id, dst_path=local_path)
    return local_path


def download_seismic(force_download: bool = False) -> Path:
    """
    Trả về path tới file data/seismic.csv.

    - Chỉ tải từ Drive nếu:
        + file chưa tồn tại, hoặc
        + force_download = True
    - Luôn giữ đúng tên: seismic.csv.
    """
    cfg = load_config()["geothermal"]
    file_id = cfg["seismic"]

    local_path = PROJECT_ROOT / "data" / "seismic.csv"
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists():
        if not force_download:
            return local_path
        local_path.unlink()

    download_from_drive(file_id=file_id, dst_path=local_path)
    return local_path


if __name__ == "__main__":
    # Test chạy riêng file này để tải raw CSV (ngoài Streamlit)
    op_path = download_operation(force_download=True)
    sei_path = download_seismic(force_download=True)
    print("Operation downloaded to:", op_path)
    print("Seismic   downloaded to:", sei_path)
