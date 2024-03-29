# -*- coding: utf-8 -*-
"""Database module for Hex."""
import datetime

from google.cloud import firestore


def get_book_puzzles(code):
    """Return a list of puzzles for a book."""
    if not code:
        return []
    client = firestore.Client()
    query = client.collection("puzzles")
    query = query.where("books", "array_contains", code)
    puzzles = []
    for doc in query.stream():
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id
        puzzles.append(puzzle)
    return sorted(puzzles, key=lambda x: x.get("date"))


def get_collection(collection):
    """Return a list of dicts from a collection."""
    client = firestore.Client()
    items = []
    for doc in client.collection(collection).stream():
        item = doc.to_dict()
        item["id"] = doc.id
        items.append(item)
    return items


def get_collection_dict(collection, key="id"):
    """Return a collection as a dict by key."""
    data = {}
    for item in get_collection(collection):
        k = item.get(key)
        if not k:
            continue
        data[k] = item
    return data


def get_doc(collection, document):
    """Return a dict from a collection."""
    client = firestore.Client()
    doc = client.collection(collection).document(document).get()
    return doc


def get_doc_dict(collection, document):
    """Return a dict from a collection."""
    doc = get_doc(collection, document)
    item = doc.to_dict()
    if item:
        item["id"] = doc.id
        return item
    return {}


def get_pagination(collection, current_item, order_by):
    """Return the next page and previous page for pagination."""
    next_item_id = get_next_item_id(collection, current_item, order_by)
    previous_item_id = get_previous_item_id(collection, current_item, order_by)
    pagination = {
        "next": next_item_id,
        "previous": previous_item_id,
    }
    return pagination


def get_next_item_id(collection, current_item, order_by):
    """Get next item for pagination."""
    query = firestore.Client().collection(collection)
    if order_by:
        query = query.order_by(order_by)
    query = query.start_after(current_item).limit(1)
    for doc in query.get():
        return doc.id
    return None


def get_previous_item_id(collection, current_item, order_by):
    """Get previous item for pagination."""
    desc = firestore.Query.DESCENDING
    query = firestore.Client().collection(collection)
    if order_by:
        query = query.order_by(order_by, direction=desc)
    query = query.start_after(current_item).limit(1)
    for doc in query.get():
        return doc.id
    return None


def get_publication(code):
    """Return a user from Firestore."""
    client = firestore.Client()
    query = client.collection("publications").where("code", "==", code).stream()
    for doc in query:
        publication = doc.to_dict()
        publication["id"] = doc.id
        return publication


def get_publication_puzzles(code):
    """Return a list of puzzles for a publication."""
    if not code:
        return []
    client = firestore.Client()
    query = client.collection("puzzles")
    query = query.where("pub", "==", code)
    puzzles = []
    for doc in query.stream():
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id
        puzzles.append(puzzle)
    return sorted(puzzles, key=lambda x: x.get("date"))


def get_puzzle_by_date(date_string, pub):
    """Return a puzzle by date."""
    date = datetime.datetime.strptime(date_string, "%Y-%m-%d")
    print(date)
    client = firestore.Client()
    query = client.collection("puzzles")
    query = query.where("date", "==", date)
    for doc in query.stream():
        puzzle = doc.to_dict()
        if puzzle["pub"] == "pub":
            return puzzle


def get_solved_puzzle(puzzle_id, user_id):
    """Return a doc respresenting a solved puzzle."""
    client = firestore.Client()
    query = client.collection("solves")
    query = query.where("puzzle_id", "==", puzzle_id)
    query = query.where("user_id", "==", user_id)
    for doc in query.stream():
        return doc.id


def get_solved_puzzles(user_id):
    """Return a doc respresenting a solved puzzle."""
    client = firestore.Client()
    query = client.collection("solves")
    query = query.where("user_id", "==", user_id)
    puzzle_ids = []
    for doc in query.stream():
        puzzle_ids.append(doc.get("puzzle_id"))
    return puzzle_ids


def save_doc(collection, document, data):
    """Return a user from Firestore."""
    client = firestore.Client()
    return client.collection(collection).document(document).set(data)
