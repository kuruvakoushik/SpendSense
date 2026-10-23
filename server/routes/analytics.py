"""Analytics API routes."""

from __future__ import annotations

from datetime import date

from flask import Blueprint, g, request

from server.auth import login_required
from server.http import fail, ok
from server.services.finance import analytics_overview, monthly_trends, month_bounds
from server.validators import ValidationError, parse_iso_date, parse_month_year

bp = Blueprint("analytics_api", __name__)


@bp.get("/overview")
@login_required
def overview():
    today = date.today()
    try:
        start = request.args.get("start")
        end = request.args.get("end")
        if start or end:
            if not start or not end:
                raise ValidationError("Both start and end dates are required.", "start")
            start = parse_iso_date(start, "start")
            end = parse_iso_date(end, "end")
            if start > end:
                raise ValidationError("Start date must be on or before the end date.", "start")
        else:
            month, year = parse_month_year(
                request.args.get("month", today.month),
                request.args.get("year", today.year),
            )
            start, end = month_bounds(year, month)
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    return ok(analytics_overview(g.user["id"], start, end))


@bp.get("/monthly-trends")
@login_required
def trends():
    today = date.today()
    try:
        month, year = parse_month_year(
            request.args.get("month", today.month),
            request.args.get("year", today.year),
        )
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    return ok(monthly_trends(g.user["id"], months=6, end_year=year, end_month=month))


@bp.get("/category-breakdown")
@login_required
def category_breakdown():
    today = date.today()
    try:
        month, year = parse_month_year(
            request.args.get("month", today.month),
            request.args.get("year", today.year),
        )
    except ValidationError as exc:
        return fail(exc.message, 400, "validation_error")
    start, end = month_bounds(year, month)
    data = analytics_overview(g.user["id"], start, end)
    return ok(data["category_breakdown"])
