"""Hex Admin — run with: python -m services.admin"""

from .app import create_app

app = create_app()
app.run(debug=True, host="0.0.0.0", port=8080)  # noqa: S104
