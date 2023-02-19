# -*- coding: utf-8 -*-
"""Cloud Function to sync data from Drive to Cloud Storage."""
import base64
import binascii
import io

from google.cloud import firestore
from google.cloud import storage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
# import google.auth
# from google.cloud import secretmanager
# import requests

BUCKET = "lukwam-hex-archive"


def get_archive_puzzles():
    """Return a list of puzzles for the archive."""
    puzzles = []
    for doc in get_puzzles():
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id
        if puzzle["pub"] in ["atlantic", "np", "nyt-acrostic", "wsj"]:
            puzzles.append(puzzle)
    return puzzles


def get_archive_puzzle_names(puzzles):
    """Return a dict of puzzles by name for the archive."""
    names = {}
    for puzzle in puzzles:
        title = puzzle["title"]
        if puzzle["pub"] == "atlantic":
            date = str(puzzle["date"])[:7]
        else:
            date = str(puzzle["date"])[:10]

        # google doc
        doc = f"{date} {title}"
        names[doc] = puzzle

        # puzzle pdf
        puzzle_pdf = f"{date} {title}.pdf"
        names[puzzle_pdf] = puzzle

        # solution pdf
        solution_pdf = f"{date} {title} (solution).pdf"
        names[solution_pdf] = puzzle

        # puzzle svg
        puzzle_svg = f"{date} {title}.svg"
        names[puzzle_svg] = puzzle

        # solution svg
        solution_svg = f"{date} {title} (solution).svg"
        names[solution_svg] = puzzle

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


def get_drive_files():
    """Get PDFs from Drive."""
    service = build("drive", "v3")
    files = service.files()
    fields = "files(id,name,mimeType,driveId,md5Checksum,modifiedTime,size),nextPageToken"
    query = (
        "mimeType != 'application/vnd.google-apps.document'"
        " and mimeType != 'application/vnd.google-apps.folder'"
        " and mimeType != 'application/vnd.google-apps.spreadsheet'"
        # " and '16gAEPIqARsXaHjtzhZUBrZgJwqVl2utN' in parents"
        " and trashed = false"
    )
    params = {
        "corpora": "drive",
        "driveId": "0ALCeSdEPSCR-Uk9PVA",
        "fields": fields,
        "includeItemsFromAllDrives": True,
        "orderBy": "name",
        "pageSize": 1000,
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


def list_drive_files(drive_files, puzzle_names):
    """Return a dict of files that should be in cloud storage."""
    files = {}

    for drive_file in drive_files:
        file_id = drive_file["id"]
        name = drive_file["name"]

        if name not in puzzle_names:
            if not name.endswith(".png"):
                print(f"Name not found in Firestore: {name}")
            continue

        puzzle = puzzle_names[name]
        pub = puzzle["pub"]
        puzzle_id = puzzle["id"]

        # set object names for cloud storage
        puzzle_pdf = f"{pub}/{puzzle_id}_puzzle.pdf"
        solution_pdf = f"{pub}/{puzzle_id}_solution.pdf"
        puzzle_svg = f"{pub}/{puzzle_id}_puzzle.svg"
        solution_svg = f"{pub}/{puzzle_id}_solution.svg"

        solution = False
        if " (solution)" in name:
            solution = True

        # handle puzzle/solution pdfs
        if name.endswith(".pdf"):
            if name.endswith(" (solution).pdf"):
                file_type = "Solution PDF"
                object_name = solution_pdf
            else:
                file_type = "Puzzle PDF"
                object_name = puzzle_pdf

        # handle puzzle/solution svgs
        elif name.endswith(".svg"):
            if name.endswith(" (solution).svg"):
                file_type = "Solution SVG"
                object_name = solution_svg
            else:
                file_type = "Puzzle SVG"
                object_name = puzzle_svg

        # skip others
        else:
            continue

        data = {
            "date": str(puzzle["date"])[:10],
            "file_id": file_id,
            "file_type": file_type,
            "issue": puzzle.get("issue", ""),
            "md5_checksum": drive_file["md5Checksum"],
            "mime_type": drive_file["mimeType"],
            "modified_time": drive_file["modifiedTime"],
            "name": name,
            "object_name": object_name,
            "pub": puzzle["pub"],
            "puzzle_id": puzzle_id,
            "size": drive_file["size"],
            "solution": str(solution),
            "title": puzzle["title"],
        }

        files[object_name] = data

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
    update = {}

    # check for files to add
    for filename in sorted(drive_files):
        if filename not in storage_files:
            add[filename] = drive_files[filename]

    # check for files to delete
    for filename in sorted(storage_files):
        if filename not in drive_files:
            delete.append(storage_files[filename])

    # check for files to update
    for filename in sorted(storage_files):
        if filename not in drive_files:
            continue
        d = drive_files[filename]
        blob = storage_files[filename]
        output = []
        if d != blob.metadata:
            keys = list(set(list(d) + list(blob.metadata)))
            for key in sorted(keys):
                o = blob.metadata.get(key)
                n = d.get(key)
                if o != n:
                    output.append(f" * {key}: {o} -> {n}")

        # update metadata if there are changes
        if output:
            print(f"\nUpdates for {filename}:")
            print("\n".join(output))
            # blob.metadata = d
            # blob.update()

        # check md5
        blob_hash = binascii.hexlify(base64.urlsafe_b64decode(blob.md5_hash)).decode()
        file_hash = d["md5_checksum"]
        if output or blob_hash != file_hash:
            add[filename] = drive_files[filename]
            # update[filename] = (d, blob)
            # print(f"\nUpdate file {filename}: {blob_hash} -> {file_hash}")

    if add:
        print(f"\nAdding {len(add)} files.")
        for filename in sorted(add, key=lambda x: drive_files[x]["name"]):
            info = drive_files[filename]
            file_id = info["file_id"]
            name = info["name"]

            # set mime type
            mime_type = info["mime_type"]
            if filename.endswith(".svg"):
                mime_type = "image/svg+xml"

            contents = get_drive_file(file_id)
            blob = bucket.blob(filename)
            blob.metadata = info

            # upload file
            print(f" + {name} [{filename}]")
            blob.upload_from_file(contents, content_type=mime_type)

    if delete:
        print(f"Deleting {len(delete)} files.")
        for blob in delete:
            print(f" - {blob.name}")
            blob.delete()

    if update:
        print(f"Updating {len(update)} files.")


def drive_to_storage(request):
    """Sync Drive data to Cloud Storage."""
    # get files from hex archive in Drive
    drive_files = get_drive_files()
    print(f"Drive Files: {len(drive_files)}")

    # get puzzles from firestore
    puzzles = get_archive_puzzles()
    print(f"Puzzles in Firestore: {len(puzzles)}")

    # get archive puzzles from firestore by Drive file name
    puzzle_names = get_archive_puzzle_names(puzzles)
    print(f"Archive Puzzle Names: {len(puzzle_names)}")

    # get a list of files from storage
    storage_files = list_storage_files()
    print(f"Storage Files: {len(storage_files)}")

    # get drive files by name
    drive_file_names = list_drive_files(drive_files, puzzle_names)
    print(f"Drive File Name: {len(drive_file_names)}")

    # update files in storage
    update_storage(drive_file_names, storage_files)

    return "ok"


if __name__ == "__main__":
    drive_to_storage(None)
