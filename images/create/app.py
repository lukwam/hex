# -*- coding: utf-8 -*-
import os

from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)


@app.route("/")
def index():
    name = os.environ.get("NAME", "World")
    return "Hello {}!".format(name)


@app.route("/puz")
def puz_v1():
    return render_template(
        "puz_v1.html",
    )


@app.route("/puz/create", methods=["GET", "POST"])
def puz_v1_create():
    puzzle = {
        "title": request.form.get("title"),
        "author": request.form.get("author"),
        "copyright": request.form.get("copyright"),
        "size": request.form.get("size"),
        "grid": [i.strip() for i in request.form.get("grid").split("\n")],
        "across": [i.strip() for i in request.form.get("across").split("\n")],
        "down": [i.strip() for i in request.form.get("down").split("\n")],
        "notepad": request.form.get("notepad"),
    }
    return render_template(
        "puz_v1.txt",
        puzzle=puzzle,
    )


@app.route("/puz2")
def puz_v2():
    return render_template(
        "puz_v1.html",
    )


@app.route("/puz2/create", methods=["GET", "POST"])
def puz_v2_create():
    puzzle = {
        "title": request.form.get("title"),
        "author": request.form.get("author"),
        "copyright": request.form.get("copyright"),
        "size": request.form.get("size"),
        "grid": [i.strip() for i in request.form.get("grid").split("\n")],
        "across": [i.strip() for i in request.form.get("across").split("\n")],
        "down": [i.strip() for i in request.form.get("down").split("\n")],
        "notepad": request.form.get("notepad"),
    }
    return render_template(
        "puz_v2.txt",
        puzzle=puzzle,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
