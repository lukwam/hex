# -*- coding: utf-8 -*-
"""Hex app."""
import datetime

import auth
import db
import helpers
from flask import Flask
from flask import g
from flask import make_response
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from google.cloud import firestore

app = Flask(__name__)

DEBUG = False


@app.before_request
def before_request():
    """Before request function."""
    g.user = None
    g.user_id = request.cookies.get("user_id")
    if g.user_id:
        g.user = auth.User(g.user_id).get()
        if g.user.admin:
            print(f"Admin: {g.user.email} [{g.user.id}]")
        else:
            print(f"User: {g.user.email} [{g.user.id}]")


#
# User Interface
#
@app.route("/")
def index():
    """Display the main index page."""
    body = render_template(
        "index.html",
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/callback", methods=["GET", "POST"])
def callback():
    # validate csrf token
    if not auth.validate_csrf_token():
        return redirect("/")

    # validate id token (credential)
    token_info = auth.validate_credential()
    if not token_info:
        return redirect("/")

    # initialize user object
    user = auth.User().from_token_info(token_info)

    # set cookie for signed-in users
    response = make_response(redirect("/"))
    if user.id and user.email:
        print(f"User signed in successfully: {user.email} [{user.id}]")
        user.save()
        response.set_cookie("user_id", user.id)
    return response


@app.route("/books")
def books_list():
    """Display the books page."""
    books = db.get_collection("books")
    for book in books:
        book_id = book["id"]
        book["cover_url"] = helpers.get_image_url(f"{book_id}_cover.png")
    body = render_template(
        "books.html",
        books=books,
        user=g.user,
    )
    return helpers.render_theme(body, title="Hex Books")


@app.route("/books/<book_id>")
def books_view(book_id):
    book = db.get_doc_dict("books", book_id)
    code = book.get("code")
    cover_url = helpers.get_image_url(f"{book_id}_cover.png")
    puzzles = db.get_book_puzzles(code)
    body = render_template(
        "book.html",
        book=book,
        cover_url=cover_url,
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Book: {book['title']}")


@app.route("/profile")
def profile():
    """Display the profile page."""
    body = render_template(
        "profile.html",
        user=g.user,
    )
    return helpers.render_theme(body, title="Profile")


@app.route("/publications")
def publications_list():
    """Display the publications list page."""
    publications = db.get_collection("publications")
    body = render_template(
        "publications.html",
        publications=publications,
        user=g.user,
    )
    return helpers.render_theme(body, title="Hex Publications")


@app.route("/publications/<publication_id>")
def publications_view(publication_id):
    """Display the publications view page."""
    publication = db.get_doc_dict("publications", publication_id)
    code = publication.get("code")
    puzzles = db.get_publication_puzzles(code)
    body = render_template(
        "publication.html",
        publication=publication,
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Publication: {publication['name']}")


@app.route("/puzzles")
def puzzles_list():
    """Display the puzzles page."""
    puzzles = db.get_collection("puzzles")
    body = render_template(
        "puzzles.html",
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title="Hex Puzzles")


@app.route("/puzzles/<puzzle_id>")
def puzzles_view(puzzle_id):
    """Display the puzzles view page."""
    doc = db.get_doc("puzzles", puzzle_id)
    puzzle = doc.to_dict()
    puzzle["id"] = doc.id
    pub = puzzle["pub"]

    publication = db.get_publication(pub)
    puzzle_url = helpers.get_image_url(f"{puzzle_id}_puzzle.png")
    answer_url = helpers.get_image_url(f"{puzzle_id}_answer.png")
    pagination = db.get_pagination("puzzles", doc, "date")
    body = render_template(
        "puzzle.html",
        answer_url=answer_url,
        pagination=pagination,
        publication=publication,
        puzzle_url=puzzle_url,
        puzzle=puzzle,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Puzzle: {puzzle['title']}")


@app.route("/signout")
def signout():
    """Sign out the user."""
    response = make_response(redirect("/"))
    response.set_cookie("user_id", "", expires=0)
    print(f"User signed out: {g.user.email} [{g.user.id}]")
    return response


#
# Admin Interface
#
@app.route("/admin")
def admin_index():
    """Display the admin index page."""
    if not g.user.admin:
        return redirect("/")
    body = render_template(
        "admin.html",
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/admin/books/<book_id>/edit", methods=["GET", "POST"])
def admin_books_edit(book_id):
    if not g.user.admin:
        return redirect("/")
    client = firestore.Client()
    if request.method == "POST":
        book = {
            "title": request.form.get("title"),
            "code": request.form.get("code"),
            "publisher": request.form.get("publisher"),
            "isbn-10": request.form.get("isbn-10"),
            "isbn-13": request.form.get("isbn-13"),
            "date": request.form.get("date"),
            "amazon_link": request.form.get("amazon_link"),
            "notes": request.form.get("notes"),
        }
        f = request.files["cover"]
        if f.filename.endswith(".png"):
            helpers.save_image(f"{book_id}_cover.png", f)
        client.collection("books").document(book_id).set(book)
        return redirect(f"/books/{book_id}")
    elif request.method == "GET":
        book = db.get_doc_dict("books", book_id)
        code = book.get("code")
        puzzles = db.get_book_puzzles(code)
        body = render_template(
            "book_edit.html",
            book=book,
            puzzles=puzzles,
            user=g.user,
        )
        return helpers.render_theme(body)


@app.route("/admin/publications/<publication_id>/edit")
def admin_publications_edit(publication_id):
    """Display the publications edit page."""
    if not g.user.admin:
        return redirect("/")
    publication = db.get_doc_dict("publications", publication_id)
    body = render_template(
        "publication_edit.html",
        publication=publication,
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/admin/puzzles/<puzzle_id>/delete", methods=["GET"])
def admin_puzzles_delete(puzzle_id):
    if not g.user.admin:
        return redirect("/")
    client = firestore.Client()
    doc_ref = client.collection("puzzles").document(puzzle_id)
    doc_ref.delete()
    return redirect("/puzzles")


@app.route("/admin/puzzles/<puzzle_id>/edit", methods=["GET", "POST"])
def admin_puzzles_edit(puzzle_id):
    """Display the edit puzzle page."""
    if not g.user.admin:
        return redirect("/")
    client = firestore.Client()

    if request.method == "POST":
        answer_link = request.form.get("answer_link")
        books = []
        for book in request.form.get("books").split(","):
            if book.strip():
                books.append(book.strip())
        date = request.form.get("date")
        issue = request.form.get("issue")
        num = request.form.get("num")
        pub = request.form.get("publication")
        puzzle_link = request.form.get("puzzle_link")
        title = request.form.get("title")
        web_link = request.form.get("web_link")

        # get puzzle image
        if puzzle_link:
            helpers.cache_image(puzzle_id, "puzzle", puzzle_link)

        # get answer image
        if answer_link:
            helpers.cache_image(puzzle_id, "answer", answer_link)

        puzzle = {
            "answer_link": answer_link,
            "books": books,
            "date": datetime.datetime.strptime(date, "%Y-%m-%d"),
            "issue": issue,
            "num": num,
            "pub": pub,
            "puzzle_link": puzzle_link,
            "title": title,
            "web_link": web_link,
        }
        client.collection("puzzles").document(puzzle_id).set(puzzle)
        return redirect(f"/puzzles/{puzzle_id}")
    else:
        # get puzzle
        doc = client.collection("puzzles").document(puzzle_id).get()
        puzzle = doc.to_dict()
        puzzle["id"] = doc.id

        # get publications
        publications = [
            pub.to_dict() for pub in sorted(
                client.collection("publications").stream(),
                key=lambda x: x.get("name"),
            )
        ]
        body = render_template(
            "puzzle_edit.html",
            publications=publications,
            puzzle=puzzle,
        )
        return helpers.render_theme(body)


@app.route("/admin/puzzles/add", methods=["GET", "POST"])
def admin_puzzles_add():
    if not g.user.admin:
        return redirect("/")
    if request.method == "GET":
        publications = db.get_collection("publications")
        body = render_template(
            "puzzle_edit.html",
            publications=publications,
            puzzle={},
        )
        return helpers.render_theme(body)
    elif request.method == "POST":
        client = firestore.Client()
        answer_link = request.form.get("answer_link")
        books = []
        for book in request.form.get("books").split(","):
            if book.strip():
                books.append(book.strip())
        date = request.form.get("date")
        issue = request.form.get("issue")
        num = request.form.get("num")
        pub = request.form.get("publication")
        puzzle_link = request.form.get("puzzle_link")
        title = request.form.get("title")
        web_link = request.form.get("web_link")

        puzzle = {
            "answer_link": answer_link,
            "books": books,
            "date": date,
            "issue": issue,
            "num": num,
            "pub": pub,
            "puzzle_link": puzzle_link,
            "title": title,
            "web_link": web_link,
        }
        client.collection("puzzles").document().set(puzzle)
        return redirect("/puzzles")


if __name__ == "__main__":
    DEBUG = True

    @app.route("/favicon.ico")
    def favicon():
        """Return favicon.ico."""
        return send_file("favicon.ico", mimetype="image/x-icon")

    @app.route("/images/<name>")
    def images(name):
        """Return static images as PNG."""
        return send_file(f"images/{name}", mimetype="image/png")

    @app.route("/styles.css")
    def styles():
        """Return data in Firestore."""
        return send_file("styles.css", mimetype="text/css")

    app.run(host="0.0.0.0", port=8080, debug=DEBUG)
