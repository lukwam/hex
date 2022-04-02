# -*- coding: utf-8 -*-
"""PDF to PNG."""
import os

from flask import Flask
from flask import request

app = Flask(__name__)


@app.route("/", methods=["POST"])
def index():
    event = request.get_json()

    bucket_name = event["bucket"]
    content_type = event["contentType"]
    file_name = event["name"]

    path = f"g://{bucket_name}/{file_name}"
    print(f"Path: {path} [{content_type}")

    return "ok"


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
