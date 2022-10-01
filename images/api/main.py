# -*- coding: utf-8 -*-
"""Hex API."""
import datetime
import os

from flask import Flask
from flask import request
from flask.json import JSONEncoder
from google.cloud import firestore


class MyJSONEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        return super().default(obj)


class MyFlask(Flask):
    json_encoder = MyJSONEncoder


app = MyFlask(__name__)


def get_collection(collection):
    """Return a collection of dicts from Firestore."""
    client = firestore.Client()
    ref = client.collection(collection)
    return get_collection_by_ref(ref)


def get_collection_by_ref(ref):
    """Return a collection of dicts from Firestore."""
    items = []
    for doc in ref.stream():
        items.append(doc.to_dict())
    return items


def get_books():
    """Return a list of Books."""
    client = firestore.Client()
    ref = client.collection("books")
    books = get_collection_by_ref(ref)
    response = {
        "books": books,
    }
    return response


def get_publications():
    """Return a list of publications."""
    client = firestore.Client()
    ref = client.collection("publications")
    publications = get_collection_by_ref(ref)
    response = {
        "publications": publications,
    }
    return response


def get_puzzles(book=None, pub=None, year=None):
    """Return a list of puzzles."""
    client = firestore.Client()
    ref = client.collection("puzzles")
    if book:
        ref = ref.where("books", "array_contains", book)
    if pub:
        ref = ref.where("pub", "==", pub)
    if year:
        start = datetime.datetime.strptime(f"{year}-01-01", "%Y-%m-%d")
        end = datetime.datetime.strptime(f"{year}-12-31", "%Y-%m-%d")
        ref = ref.where("date", ">=", start).where("date", "<=", end)
    puzzles = get_collection_by_ref(ref)
    response = {
        "puzzles": puzzles,
    }
    return response


@app.route("/")
def index():
    return "ok"


@app.route("/books")
def list_books():
    """List Books API endpoint."""
    books = get_books()
    print(f"Books: {len(books)}")
    return books


@app.route("/publications")
def list_publications():
    """List Publications API endpoint."""
    publications = get_publications()
    print(f"Publications: {len(publications)}")
    return publications


@app.route("/puzzles")
def list_puzzles():
    """List Puzzles API endpoint."""
    book = request.args.get("book")
    pub = request.args.get("pub")
    year = request.args.get("year")
    puzzles = get_puzzles(
        book=book,
        pub=pub,
        year=year,
    )
    print(f"Puzzles: {len(puzzles)}")
    return puzzles


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
