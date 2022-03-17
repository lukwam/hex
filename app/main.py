from flask import Flask
from flask import render_template

app = Flask(__name__)


def render_theme(body, **kwargs):
    """Return the rendered theme."""
    return render_template(
        "theme.html",
        body=body,
        **kwargs
    )


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    body = render_template(
        "index.html",
    )
    return render_theme(body)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
