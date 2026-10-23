"""Start the SpendSense Flask development server."""

from __future__ import annotations

import os

from server.app import create_app

app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=debug)
