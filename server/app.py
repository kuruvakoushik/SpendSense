"""Flask application factory."""

from __future__ import annotations

import logging
from datetime import timedelta

from flask import Flask, g, redirect, request, send_from_directory, session
from flask_wtf.csrf import CSRFError, CSRFProtect

from server.auth import current_user
from server.config import BASE_DIR, Config, resolve_database_path
from server.database import close_db, init_db
from server.http import fail
from server.routes.analytics import bp as analytics_bp
from server.routes.auth import bp as auth_bp
from server.routes.budgets import bp as budgets_bp
from server.routes.categories import bp as categories_bp
from server.routes.dashboard import bp as dashboard_bp
from server.routes.insights import bp as insights_bp
from server.routes.profile import bp as profile_bp
from server.routes.transactions import bp as transactions_bp
from server.validators import ValidationError

CLIENT_DIR = BASE_DIR / "client"
PUBLIC_ASSETS_DIR = BASE_DIR / "public" / "assets"
PROTECTED_PAGES = {
    "dashboard.html",
    "transactions.html",
    "categories.html",
    "budgets.html",
    "analytics.html",
    "insights.html",
    "profile.html",
}

csrf = CSRFProtect()


def create_app(config_object=None) -> Flask:
    app = Flask(
        __name__,
        static_folder=None,
    )
    app.config.from_object(config_object or Config)
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["WTF_CSRF_SSL_STRICT"] = False

    if (
        app.config.get("APP_ENV") == "production"
        and (
            not app.config.get("SECRET_KEY")
            or len(app.config["SECRET_KEY"]) < 32
            or app.config["SECRET_KEY"] == "dev-only-insecure-secret-change-me"
        )
    ):
        raise RuntimeError("Production requires a unique SECRET_KEY of at least 32 characters.")

    logging.basicConfig(level=logging.INFO)
    csrf.init_app(app)
    init_db(resolve_database_path(app.config["DATABASE_PATH"]))

    app.teardown_appcontext(close_db)

    @app.before_request
    def load_user():
        g.user = current_user()

    @app.errorhandler(CSRFError)
    def handle_csrf(_error):
        return fail("Your session token expired. Refresh the page and try again.", 400, "csrf_failed")

    @app.errorhandler(404)
    def handle_404(_error):
        if request.path.startswith("/api/"):
            return fail("The requested resource was not found.", 404, "not_found")
        return send_from_directory(CLIENT_DIR, "404.html"), 404

    @app.errorhandler(413)
    def handle_413(_error):
        return fail("The request is too large.", 413, "payload_too_large")

    @app.errorhandler(ValidationError)
    def handle_validation(error):
        return fail(error.message, 400, "validation_error")

    @app.errorhandler(Exception)
    def handle_unexpected(error):
        app.logger.exception("Unhandled error: %s", error)
        if app.config.get("TESTING"):
            raise error
        return fail("Something went wrong. Please try again.", 500, "server_error")

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")
    app.register_blueprint(transactions_bp, url_prefix="/api/transactions")
    app.register_blueprint(categories_bp, url_prefix="/api/categories")
    app.register_blueprint(budgets_bp, url_prefix="/api/budgets")
    app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    app.register_blueprint(insights_bp, url_prefix="/api/insights")
    app.register_blueprint(profile_bp, url_prefix="/api/profile")

    @app.get("/")
    def landing():
        return send_from_directory(CLIENT_DIR, "index.html")

    @app.get("/assets/<path:asset_path>")
    def static_assets(asset_path: str):
        # The same files live in Vercel's public/assets CDN directory. This
        # route serves them when running locally with Flask's dev server.
        return send_from_directory(PUBLIC_ASSETS_DIR, asset_path)

    @app.get("/<page>")
    def html_page(page: str):
        filename = page if page.endswith(".html") else f"{page}.html"
        target = CLIENT_DIR / filename
        if not target.is_file():
            return send_from_directory(CLIENT_DIR, "404.html"), 404
        if filename in PROTECTED_PAGES and session.get("user_id") is None:
            return redirect("/login")
        if filename in {"login.html", "register.html"} and session.get("user_id"):
            return redirect("/dashboard")
        return send_from_directory(CLIENT_DIR, filename)

    return app

