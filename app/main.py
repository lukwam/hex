# -*- coding: utf-8 -*-
"""Hex app."""
import datetime

import auth
import dateparser
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
# import io
# import json
# import re
# from google.cloud import storage

app = Flask(__name__)

DEBUG = False


@app.before_request
def before_request():
    """Before request function."""
    g.admin = False
    g.user = None
    g.user_id = request.cookies.get("user_id")
    if g.user_id:
        g.user = auth.User(g.user_id).get()
        g.admin = g.user.admin
        if g.user.admin:
            print(f"Admin: {g.user.email} [{g.user.id}]")
        else:
            print(f"User: {g.user.email} [{g.user.id}]")

    if DEBUG:
        g.admin = True
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


# @app.route("/new")
# def new_index():
#     """Display the main index page."""
#     return render_template("index_new.html", user=g.user)


@app.route("/archive")
def archive():
    """Display the archive index page."""
    if not g.admin:
        return redirect("/")
    bucket = "lukwam-hex-archive"

    # atlantic archive
    atlantic = db.get_publication_puzzles("atlantic")
    atlantic_objects = helpers.get_objects(bucket, prefix="atlantic/")
    atlantic_years = []
    for puzzle in atlantic:
        year = str(puzzle["date"])[:4]
        if year not in atlantic_years:
            atlantic_years.append(year)

    # wsj archive
    wsj = db.get_publication_puzzles("wsj")
    wsj_objects = helpers.get_objects(bucket, prefix="wsj/")
    wsj_years = []
    for puzzle in wsj:
        year = str(puzzle["date"])[:4]
        if year not in wsj_years:
            wsj_years.append(year)

    body = render_template(
        "archive.html",
        atlantic=atlantic,
        atlantic_years=sorted(atlantic_years),
        atlantic_objects=atlantic_objects,
        wsj=wsj,
        wsj_years=sorted(wsj_years),
        wsj_objects=wsj_objects,
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/archive/report")
def archive_report():
    """Display a report about the archive."""
    if not g.admin:
        return redirect("/")
    bucket = "lukwam-hex-archive"

    # atlantic archive
    atlantic = {}
    objects = helpers.get_objects(bucket, prefix="atlantic/")
    for puzzle in db.get_publication_puzzles("atlantic"):
        puzzle_id = puzzle["id"]
        date = str(puzzle["date"])[:10]
        title = puzzle["title"]
        year = date[:4]

        if f"atlantic/{puzzle_id}_puzzle.pdf" not in objects:
            if year not in atlantic:
                atlantic[year] = []
            atlantic[year].append({"name": f"{date} {title}.pdf"})

        if f"atlantic/{puzzle_id}_solution.pdf" not in objects:
            if year not in atlantic:
                atlantic[year] = []
            atlantic[year].append({"name": f"{date} {title} (solution).pdf"})

    # wsj archive
    wsj = {}
    objects = helpers.get_objects(bucket, prefix="wsj/")
    for puzzle in db.get_publication_puzzles("wsj"):
        puzzle_id = puzzle["id"]
        date = str(puzzle["date"])[:10]
        title = puzzle["title"]
        year = date[:4]

        if f"wsj/{puzzle_id}_puzzle.pdf" not in objects:
            if year not in wsj:
                wsj[year] = []
            wsj[year].append({"name": f"{date} {title}.pdf"})

        if f"wsj/{puzzle_id}_solution.pdf" not in objects:
            if year not in wsj:
                wsj[year] = []
            wsj[year].append({"name": f"{date} {title} (solution).pdf"})

    body = render_template(
        "archive_report.html",
        atlantic=atlantic,
        wsj=wsj,
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/archive/<pub>/<year>")
def archive_year(pub, year):
    """Display the archive for a specific year."""
    if not g.admin:
        return redirect("/")
    if pub == "atlantic":
        publication = "The Atlantic Puzzler"
        first_year = 1977
        last_year = 2009

        prev_year = int(year) - 1 if int(year) > first_year else None
        next_year = int(year) + 1 if int(year) < last_year else None

    elif pub == "wsj":
        publication = "The Wall Street Journal"
        first_year = 2010
        last_year = int(str(datetime.date.today())[:4])

        prev_year = int(year) - 1 if int(year) > first_year else None
        next_year = int(year) + 1 if int(year) < last_year else None

    else:
        return redirect("/")

    puzzles = {}
    for puzzle in db.get_publication_puzzles(pub):
        if str(puzzle["date"])[:4] == year:
            puzzle_id = puzzle["id"]
            puzzles[puzzle_id] = puzzle

    bucket = "lukwam-hex-thumbnails"
    images = []
    for image in helpers.get_objects(bucket, prefix=f"{pub}/"):
        puzzle_id = image.split("/")[1].split("_")[0]
        if puzzle_id not in puzzles:
            continue
        puzzle = puzzles[puzzle_id]
        url = helpers.generate_download_signed_url_v4(bucket, image)
        if "_puzzle.png" in image:
            puzzle["puzzle_image_url"] = url
        elif "_solution.png" in image:
            puzzle["solution_image_url"] = url
        else:
            print(f"Unknown image type: {image}")

    body = render_template(
        "archive_year.html",
        images=images,
        next_year=next_year,
        prev_year=prev_year,
        pub=pub,
        publication=publication,
        puzzles=puzzles.values(),
        user=g.user,
        year=year,
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
        admin=g.admin,
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
        admin=g.admin,
        book=book,
        cover_url=cover_url,
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Book: {book['title']}")


# @app.route("/download/<image_type>/<name>")
# def download_image(image_type, name):
#     """Return an image."""
#     # if user is not logged in, redirect
#     if not g.user_id:
#         return redirect("/")

#     # if puzzle time is invalid, redirect
#     if image_type not in ["puzzle", "solution"]:
#         return redirect("/")

#     # check if filename is valid
#     result = re.search(r"^(.*).(...)$", name)
#     if not result:
#         return redirect("/")

#     puzzle_id, ext = result.groups()
#     if ext not in ["pdf", "png"]:
#         return redirect("/")

#     # get puzzle
#     puzzle = db.get_doc_dict("puzzles", puzzle_id)
#     pub = puzzle["pub"]

#     # set the bucket
#     bucket_name = "lukwam-hex-archive"
#     mime_type = "application/pdf"
#     if ext == "png":
#         bucket_name = "lukwam-hex-archive-images"
#         mime_type = "image/png"

#     # get file
#     object_name = f"{pub}/{puzzle_id}_{image_type}.{ext}"
#     # tmp_file = f"/tmp/{puzzle_id}_{image_type}.{ext}"
#     f = io.BytesIO()
#     client = storage.Client()
#     bucket = client.bucket(bucket_name)
#     blob = bucket.blob(object_name)
#     blob.download_to_file(f)
#     f.seek(0)

#     return send_file(
#         f,
#         # as_attachment=True,
#         # download_name='test.csv',
#         mimetype=mime_type,
#     )


@app.route("/profile")
def profile():
    """Display the profile page."""
    if not g.user.id:
        return redirect("/")
    solves = db.get_solved_puzzles(g.user_id)
    solved = {}
    solved_count = 0
    unsolved = {}
    unsolved_count = 0
    for puzzle in db.get_collection("puzzles"):
        pub = puzzle["pub"]
        if puzzle["id"] in solves:
            if pub not in solved:
                solved[pub] = []
            solved[pub].append(puzzle)
            solved_count += 1
        else:
            if pub not in unsolved:
                unsolved[pub] = []
            unsolved[pub].append(puzzle)
            unsolved_count += 1
    body = render_template(
        "profile.html",
        solved=solved,
        solved_count=solved_count,
        unsolved=unsolved,
        unsolved_count=unsolved_count,
        user=g.user,
    )
    return helpers.render_theme(body, title="Profile")


@app.route("/publications")
def publications_list():
    """Display the publications list page."""
    publications = db.get_collection("publications")
    body = render_template(
        "publications.html",
        admin=g.admin,
        publications=publications,
        user=g.user,
    )
    return helpers.render_theme(body, title="Hex Publications")


@app.route("/pubs/<code>")
def pubs_view(code):
    """View a specific publication by code."""
    pubs = db.get_collection("publications")
    for pub in pubs:
        if pub["code"] == code:
            pub_id = pub["id"]
            return redirect(f"/publications/{pub_id}")


@app.route("/publications/<publication_id>")
def publications_view(publication_id):
    """Display the publications view page."""
    objects = helpers.get_objects("lukwam-hex-images")
    publication = db.get_doc_dict("publications", publication_id)
    code = publication.get("code")
    puzzles = db.get_publication_puzzles(code)
    body = render_template(
        "publication.html",
        admin=g.admin,
        objects=objects,
        publication=publication,
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Publication: {publication['name']}")


@app.route("/puzzles")
def puzzles_list():
    """Display the puzzles page."""
    puzzles = db.get_collection("puzzles")
    publications = db.get_collection_dict("publications", key="code")
    for puzzle in puzzles:
        pub = puzzle["pub"]
        puzzle["date"] = puzzle["date"].date()
        puzzle["publication_name"] = publications[pub]

    # data_table = {
    #     "data": puzzles,
    #     "columns": [
    #         { "data": 'date' },
    #         { "data": 'title' },
    #         { "data": 'publication_name' },
    #     ],
    # }
    body = render_template(
        "puzzles.html",
        admin=g.admin,
        # data_table=json.dumps(data_table, default=str, sort_keys=True, indent=2),
        publications=publications,
        puzzles=puzzles,
        user=g.user,
    )
    return helpers.render_theme(body, title="Hex Puzzles")


@app.route("/puzzles/<puzzle_id>")
def puzzles_view(puzzle_id):
    """Display the puzzles view page."""
    # get puzzle (use doc for pagination)
    doc = db.get_doc("puzzles", puzzle_id)
    puzzle = doc.to_dict()
    puzzle["id"] = doc.id

    # get pagination
    pagination = db.get_pagination("puzzles", doc, "date")

    # get publication
    publication = db.get_publication(puzzle["pub"])

    # get signed urls for images
    puzzle_url = helpers.get_image_url(f"{puzzle_id}_puzzle.png")
    answer_url = helpers.get_image_url(f"{puzzle_id}_answer.png")

    # get a solved puzzle
    solved = False
    if g.user and g.user.id:
        solved = db.get_solved_puzzle(puzzle_id, g.user.id)

    body = render_template(
        "puzzle.html",
        admin=g.admin,
        answer_url=answer_url,
        pagination=pagination,
        publication=publication,
        puzzle_url=puzzle_url,
        puzzle=puzzle,
        solved=solved,
        user=g.user,
    )
    return helpers.render_theme(body, title=f"Hex Puzzle: {puzzle['title']}")


@app.route("/puzzles/<puzzle_id>/solve")
def puzzles_solve(puzzle_id):
    """Solve a single puzzle for a user."""
    if not g.user.id:
        return redirect("/")
    data = {
        "puzzle_id": puzzle_id,
        "user_id": g.user.id,
    }
    firestore.Client().collection("solves").document().set(data)
    return redirect(f"/puzzles/{puzzle_id}")


@app.route("/puzzles/<puzzle_id>/unsolve")
def puzzles_unsolve(puzzle_id):
    """Unsolve a single puzzle for a user."""
    if not g.user.id:
        return redirect("/")
    solve_id = db.get_solved_puzzle(puzzle_id, g.user.id)
    firestore.Client().collection("solves").document(solve_id).delete()
    return redirect(f"/puzzles/{puzzle_id}")


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
    if not g.admin:
        return redirect("/")
    body = render_template(
        "admin.html",
        user=g.user,
    )
    return helpers.render_theme(body)


@app.route("/admin/books/<book_id>/edit", methods=["GET", "POST"])
def admin_books_edit(book_id):
    if not g.admin:
        return redirect("/")
    client = firestore.Client()
    if request.method == "POST":
        book = {
            "title": request.form.get("title"),
            "code": request.form.get("code"),
            "publisher": request.form.get("publisher"),
            "source": request.form.get("source"),
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
        publications = db.get_collection("publications")
        # code = book.get("code")
        # puzzles = db.get_book_puzzles(code)
        body = render_template(
            "book_edit.html",
            book=book,
            # puzzles=puzzles,
            publications=publications,
            user=g.user,
        )
        return helpers.render_theme(body)


@app.route("/admin/publications/add", methods=["GET", "POST"])
def admin_publications_add():
    if not g.admin:
        return redirect("/")
    if request.method == "GET":
        body = render_template(
            "publication_edit.html",
            publication={},
            user=g.user,
        )
        return helpers.render_theme(body)
    elif request.method == "POST":
        client = firestore.Client()
        code = request.form.get("code")
        name = request.form.get("name")
        url = request.form.get("url")
        publication = {
            "code": code,
            "name": name,
            "url": url,
        }
        client.collection("publications").document().set(publication)
        return redirect("/publications")


@app.route("/admin/publications/<publication_id>/edit", methods=["GET", "POST"])
def admin_publications_edit(publication_id):
    """Display the publications edit page."""
    if not g.admin:
        return redirect("/")
    if request.method == "GET":
        publication = db.get_doc_dict("publications", publication_id)
        body = render_template(
            "publication_edit.html",
            publication=publication,
            user=g.user,
        )
        return helpers.render_theme(body)
    elif request.method == "POST":
        client = firestore.Client()
        code = request.form.get("code")
        name = request.form.get("name")
        url = request.form.get("url")
        publication = {
            "code": code,
            "name": name,
            "url": url,
        }
        client.collection("publications").document(publication_id).set(publication)
        return redirect("/publications")


# @app.route("/admin/puzzles")
# def admin_puzzles_list():
#     """Display the admin puzzles page."""
#     if not g.admin:
#         return redirect("/")
#     puzzles = db.get_collection("puzzles")
#     publications = db.get_collection_dict("publications", key="code")
#     archive_files = helpers.get_objects("lukwam-hex-archive")
#     print(f"Archive Files: {len(archive_files)}")
#     image_files = helpers.get_objects("lukwam-hex-archive-images")
#     print(f"Image Files: {len(image_files)}")
#     thumb_files = helpers.get_objects("lukwam-hex-thumbnails")
#     print(f"Thumbnail Files: {len(thumb_files)}")
#     body = render_template(
#         "admin_puzzles.html",
#         publications=publications,
#         puzzles=sorted(puzzles, key=lambda x: x["date"], reverse=True),
#     )
#     return helpers.render_theme(body)


@app.route("/admin/puzzles/<puzzle_id>/delete", methods=["GET"])
def admin_puzzles_delete(puzzle_id):
    if not g.admin:
        return redirect("/")
    client = firestore.Client()
    doc_ref = client.collection("puzzles").document(puzzle_id)
    doc_ref.delete()
    return redirect("/puzzles")


@app.route("/admin/puzzles/<puzzle_id>/edit", methods=["GET", "POST"])
def admin_puzzles_edit(puzzle_id):
    """Display the edit puzzle page."""
    if not g.admin:
        return redirect("/")
    client = firestore.Client()

    if request.method == "POST":
        answer_link = request.form.get("answer_link")
        books = []
        for book in request.form.get("books").split(","):
            if book.strip():
                books.append(book.strip())
        date = request.form.get("date")
        googledoc_link = request.form.get("googledoc_link")
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
            "date": dateparser.parse(date),
            "googledoc_link": googledoc_link,
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
    if not g.admin:
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
        date = dateparser.parse(request.form.get("date"))
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


@app.route("/users")
def users_list():
    if not g.admin:
        return redirect("/")
    users = db.get_collection("users")
    body = render_template(
        "users.html",
        users=users,
    )
    return helpers.render_theme(body)


#
# API
#
@app.route("/api/books")
def api_books_list():
    """Return a lit of books."""
    if not g.admin:
        return redirect("/")
    books = db.get_collection("books")
    print(f"Books: {len(books)}")
    response = {"books": books}
    return response


@app.route("/api/publications")
def api_publications_list():
    """Return a lit of publications."""
    if not g.admin:
        return redirect("/")
    publications = db.get_collection("publications")
    print(f"Publications: {len(publications)}")
    response = {"publications": publications}
    return response


@app.route("/api/puzzles")
def api_puzzles_list():
    """Return a lit of puzzles."""
    if not g.admin:
        return redirect("/")
    puzzles = db.get_collection("puzzles")
    for p in puzzles:
        p["date"] = str(p["date"].date())
    print(f"Puzzles: {len(puzzles)}")
    response = {"puzzles": puzzles}
    return response


@app.route("/api/users")
def api_users_list():
    """Return a lit of users."""
    if not g.admin:
        return redirect("/")
    users = db.get_collection("users")
    print(f"Users: {len(users)}")
    response = {"users": users}
    return response


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

    @app.route("/script.js")
    def script():
        """Return data in Firestore."""
        return send_file("script.js", mimetype="application/javascript")

    @app.route("/styles.css")
    def styles():
        """Return data in Firestore."""
        return send_file("styles.css", mimetype="text/css")

    app.run(host="0.0.0.0", port=8080, debug=DEBUG)
