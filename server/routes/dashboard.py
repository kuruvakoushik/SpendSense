"""Dashboard API routes."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from server.auth import login_required
from server.http import fail, ok
from server.services.finance import dashboard_summary, insert_demo_data, monthly_trends, recent_transactions
from server.validators import ValidationError, clamp_limit, parse_month_year

bp = Blueprint("dashboard_api", __name__)


def _period():
    today = date.today()
    month = request.args.get("month", today.month)
    year = request.args.get("year", today.year)
    return parse_month_year(month, year)


@bp.get("/summary")
@login_required
def summary():
    try:
        month, year = _period()
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    data = dashboard_summary(g.user["id"], year, month)
    data["trends"] = monthly_trends(g.user["id"], months=6, end_year=year, end_month=month)
    return ok(data)


@bp.get("/recent-transactions")
@login_required
def recent():
    limit = clamp_limit(request.args.get("limit"), 8, 25)
    return ok(recent_transactions(g.user["id"], limit))


@bp.post("/demo-data")
@login_required
def demo_data():
    payload = request.get_json(silent=True) or {}
    if not payload.get("confirm"):
        return fail("Confirm the demo-data action to continue.", 400, "confirmation_required")
    count = insert_demo_data(g.user["id"])
    return ok({"inserted": count})
