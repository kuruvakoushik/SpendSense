"""Standard Flask WSGI entry point for hosting platforms."""

from server.app import create_app

app = create_app()
