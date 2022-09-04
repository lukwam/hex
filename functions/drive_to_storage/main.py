# -*- coding: utf-8 -*-
"""Cloud Function to sync data from Drive to Cloud Storage."""
# import base64
# import google.auth
import io

from google.cloud import firestore
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
# from google.cloud import secretmanager
# import requests

BUCKET = "lukwam-hex-archive"


def get_archive_puzzles():
    """Return a list of puzzles for the archive."""
    puzzles = []
    for doc in get_puzzles():
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id
        if puzzle["pub"] in ["atlantic", "wsj"]:
            puzzles.append(puzzle)
    return puzzles


def get_archive_puzzle_names():
    """Return a dict of puzzles by name for the archive."""
    puzzles = get_archive_puzzles()
    names = {}
    for puzzle in puzzles:
        title = puzzle["title"]
        if puzzle["pub"] == "atlantic":
            date = str(puzzle["date"])[:7]
        else:
            date = str(puzzle["date"])[:10]
        name = f"{date} {title}.pdf"
        solution = f"{date} {title} (solution).pdf"
        names[name] = puzzle
        names[solution] = puzzle
    return names


def get_drive_file(file_id):
    """Return the data from a file in drive."""
    service = build("drive", "v3")
    try:
        request = service.files().get_media(
            fileId=file_id,
            supportsAllDrives=True,
        )

        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()

    except HttpError as error:
        print(f'An error occurred: {error}')
        return None

    file.seek(0)
    return file


def get_drive_pdfs():
    """Get PDFs from Drive."""
    service = build("drive", "v3")
    files = service.files()
    query = "mimeType = 'application/pdf' and trashed = false"
    # query += " and '16gAEPIqARsXaHjtzhZUBrZgJwqVl2utN' in parents"
    params = {
        "corpora": "drive",
        "driveId": "0AJjaMUx5BsM-Uk9PVA",
        "includeItemsFromAllDrives": True,
        "orderBy": "name",
        "q": query,
        "supportsAllDrives": True,
    }
    request = service.files().list(**params)
    items = []
    while request is not None:
        response = request.execute()
        items.extend(response.get("files", []))
        request = files.list_next(request, response)
    return items


def get_puzzles():
    """Get Puzzles from Firestore."""
    client = firestore.Client()
    db = client.collection("puzzles")
    return list(db.stream())


def list_drive_files(pdfs, puzzle_names):
    """Return a dict of files that should be in cloud storage."""
    files = {}

    for pdf in pdfs:
        file_id = pdf["id"]
        name = pdf["name"]

        if name not in puzzle_names:
            print(f"Name not found in Firestore: {name}")
            continue

        puzzle = puzzle_names[name]
        pub = puzzle["pub"]
        puzzle_id = puzzle["id"]

        filename = f"{pub}/{puzzle_id}_puzzle.pdf"
        solution = False
        if " (solution)" in name:
            filename = f"{pub}/{puzzle_id}_solution.pdf"
            solution = True

        files[filename] = {
            "date": str(puzzle["date"])[:10],
            "file_id": file_id,
            "issue": puzzle["issue"],
            "pub": puzzle["pub"],
            "name": name,
            "puzzle_id": puzzle_id,
            "solution": solution,
            "title": puzzle["title"],
        }
    return files


def list_storage_files():
    """Return a list of files in storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)
    files = {}
    for blob in bucket.list_blobs():
        files[blob.name] = blob
    return files


def update_storage(drive_files, storage_files):
    """Update files in Storage."""
    client = storage.Client()
    bucket = client.bucket(BUCKET)

    add = {}
    delete = []
    # update = {}

    for filename in sorted(drive_files):
        if filename not in storage_files:
            add[filename] = drive_files[filename]
    for filename in sorted(storage_files):
        if filename not in drive_files:
            delete.append(storage_files[filename])

    if add:
        print(f"Adding {len(add)} files.")
        for filename in add:
            info = drive_files[filename]
            file_id = info["file_id"]
            contents = get_drive_file(file_id)
            blob = bucket.blob(filename)
            blob.metadata = info
            blob.upload_from_file(
                contents,
                content_type="application/pdf",
            )
            print(f" + {filename}")

    if delete:
        print(f"Deleting {len(delete)} files.")
        for blob in delete:
            blob.delete()


def drive_to_storage(request):
    """Sync Drive data to Cloud Storage."""

    # get archive puzzles from firestore by Drive file name
    puzzle_names = get_archive_puzzle_names()
    print(f"Archive Puzzle Names in Firestore: {len(puzzle_names)}")

    # get PDFs from drive archive
    pdfs = get_drive_pdfs()
    print(f"PDFs: {len(pdfs)}")

    # get a list of files from drive to copy to storage
    drive_files = list_drive_files(pdfs, puzzle_names)
    print(f"Drive Files: {len(drive_files)}")

    # get a list of files from storage
    storage_files = list_storage_files()
    print(f"Storage Files: {len(storage_files)}")

    # update files in storage
    update_storage(drive_files, storage_files)

    return "ok"


if __name__ == "__main__":
    drive_to_storage(None)
