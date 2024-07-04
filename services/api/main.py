"""Hex API."""
import json
from typing import Any
from typing import List
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.cloud import firestore

import models


class PrettyJSONResponse(JSONResponse):
    """Pretty JSON Response."""

    def render(self, content: Any) -> bytes:
        """Render."""
        return json.dumps(content, indent=4, ensure_ascii=False).encode("utf-8")


app = FastAPI(
    contact={
        "name": "Lukas Karlsson",
        "email": "karlsson@altissimo.io",
    },
    default_response_class=PrettyJSONResponse,
    # dependencies=[Depends(validate_user)],
    description="Hex API",
    openapi_tags=[
        {"name": "Main", "description": "Main operations."},
    ],
    title="Hex API",
    version="0.0.1",
)
db = firestore.Client()


async def get_collection(collection: str) -> list:
    """Get a collection."""
    items = []
    for doc in db.collection(collection).stream():
        item = doc.to_dict()
        item["id"] = doc.id
        items.append(item)
    return items


async def get_collection_dict(collection: str) -> dict:
    """Get a collection as a dict."""
    items = await get_collection(collection)
    return {item["id"]: item for item in items}


#
# Endpoints
#
@app.get("/", tags=["Main"])
async def hello() -> dict:
    """Hello."""
    return {"message": "Hello World!"}


@app.get("/books", tags=["Main"])
async def list_books() -> List[models.Book]:
    """List Books."""
    books = []
    for item in await get_collection("books"):
        books.append(models.Book(**item))
    return books


@app.get("/hexgrids", tags=["Main"])
async def list_hexgrids() -> List[models.Hexgrid]:
    """List Hexgrids."""
    hexgrids = []
    for item in await get_collection("hexgrids"):
        hexgrids.append(models.Hexgrid(**item))
    return hexgrids


# @app.get("/hexgridsnew", tags=["Main"])
# async def list_hexgridsnew() -> List[models.Hexgrid]:
#     """List Hexgrids."""
#     hexgrids = []
#     for item in await get_collection("hexgridsnew"):
#         hexgrids.append(models.Hexgrid(**item))
#     return hexgrids


# @app.get("/hexgrids_backup", tags=["Main"])
# async def list_hexgrids_backup() -> List[models.Hexgrid]:
#     """List Hexgrids."""
#     hexgrids = []
#     for item in await get_collection("hexgrids_backup"):
#         hexgrids.append(models.Hexgrid(**item))
#     return hexgrids


@app.get("/publications", tags=["Main"])
async def list_publications() -> List[models.Publication]:
    """List Publications."""
    publications = []
    for item in await get_collection("publications"):
        publications.append(models.Publication(**item))
    return publications


@app.get("/puzzles", tags=["Main"])
async def list_puzzles() -> List[models.Puzzle]:
    """List Puzzles."""
    puzzles = []
    for item in await get_collection("puzzles"):
        puzzles.append(models.Puzzle(**item))
    return puzzles


@app.get("/solves", tags=["Main"])
async def list_solves() -> List[models.Solve]:
    """List Solves."""
    solves = []
    for item in await get_collection("solves"):
        solves.append(models.Solve(**item))
    return solves


@app.get("/users", tags=["Main"])
async def list_users() -> List[models.User]:
    """List Users."""
    users = []
    for item in await get_collection("users"):
        users.append(models.User(**item))
    return users
