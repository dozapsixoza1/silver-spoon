import os
import zipfile
import rarfile
import py7zr
import tarfile
import aiofiles
from config import UPLOAD_DIR
from search import index_file

rarfile.UNRAR_TOOL = "unrar"

async def save_upload(file, filename: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    path = os.path.join(UPLOAD_DIR, filename)
    async with aiofiles.open(path, 'wb') as f:
        await f.write(await file.read())
    return path

async def extract_archive(archive_path: str) -> list:
    ext = os.path.splitext(archive_path)[1].lower()
    extract_to = os.path.join(UPLOAD_DIR, "extracted_" + os.path.basename(archive_path).replace('.', '_'))
    os.makedirs(extract_to, exist_ok=True)
    extracted_files = []

    if ext == ".zip":
        with zipfile.ZipFile(archive_path, 'r') as z:
            z.extractall(extract_to)
            extracted_files = [os.path.join(extract_to, f) for f in z.namelist()]
    elif ext == ".rar":
        with rarfile.RarFile(archive_path, 'r') as r:
            r.extractall(extract_to)
            extracted_files = [os.path.join(extract_to, f) for f in r.namelist()]
    elif ext == ".7z":
        with py7zr.SevenZipFile(archive_path, 'r') as sz:
            sz.extractall(extract_to)
            for root, _, files in os.walk(extract_to):
                for f in files:
                    extracted_files.append(os.path.join(root, f))
    elif ext == ".tar" or archive_path.endswith(".tar.gz") or archive_path.endswith(".tgz"):
        mode = "r:gz" if archive_path.endswith(".gz") else "r"
        with tarfile.open(archive_path, mode) as tar:
            tar.extractall(extract_to)
            extracted_files = [os.path.join(extract_to, f) for f in tar.getnames()]
    elif archive_path.endswith(".7z.001"):
        base = archive_path.replace(".001", "")
        parts = sorted([f for f in os.listdir(UPLOAD_DIR) if f.startswith(os.path.basename(base))])
        out_path = os.path.join(UPLOAD_DIR, os.path.basename(base) + ".7z")
        with open(out_path, 'wb') as out:
            for part in parts:
                with open(os.path.join(UPLOAD_DIR, part), 'rb') as p:
                    out.write(p.read())
        with py7zr.SevenZipFile(out_path, 'r') as sz:
            sz.extractall(extract_to)
            for root, _, files in os.walk(extract_to):
                for f in files:
                    extracted_files.append(os.path.join(root, f))
    return extracted_files

async def index_extracted_files(files: list, bot, chat_id: int):
    total = 0
    for file in files:
        if file.lower().endswith(('.csv', '.xlsx', '.xls', '.txt', '.json')):
            res = index_file(file)
            total += res
            await bot.send_message(chat_id, f"📄 {os.path.basename(file)}: {res} записей")
    return total
