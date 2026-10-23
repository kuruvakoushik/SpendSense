"""Insights, forecast, and anomaly API routes."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from server.auth import login_required
from server.http import fail, ok
from server.services.anomaly_detection import build_insights, detect_anomalies
from server.services.forecasting import month_end_forecast
from server.validators import ValidationError, parse_month_year

bp = Blueprint("insights_api", __name__)


def _period():
    today = date.today()
    return parse_month_year(request.args.get("month", today.month), request.args.get("year", today.year))


@bp.get("")
@login_required
def insights():
    try:
        month, year = _period()
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    return ok(build_insights(g.user["id"], year, month))


@bp.get("/forecast")
@login_required
def forecast():
    try:
        month, year = _period()
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    return ok(month_end_forecast(g.user["id"], year, month))


@bp.get("/anomalies")
@login_required
def anomalies():
    return ok(detect_anomalies(g.user["id"]))
