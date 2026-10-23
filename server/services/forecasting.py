"""Transparent baseline month-end spending estimate."""

from __future__ import annotations

import calendar
from datetime import date

from server.services.finance import month_bounds, serialize_money, sum_for_period
from server.database import get_db


def month_end_forecast(user_id: int, year: int | None = None, month: int | None = None) -> dict:
    today = date.today()
    year = year or today.year
    month = month or today.month
    start, end = month_bounds(year, month)
    days_in_month = calendar.monthrange(year, month)[1]

    if year == today.year and month == today.month:
        elapsed_days = today.day
        remaining_days = days_in_month - today.day
        as_of = today.isoformat()
    elif date(year, month, days_in_month) < today:
        elapsed_days = days_in_month
        remaining_days = 0
        as_of = end
    else:
        return {
            "sufficient_data": False,
            "message": "This month has not started yet, so a spending estimate is not available.",
            "method": "baseline_average_daily_run_rate",
            "disclaimer": "Estimates are not guaranteed outcomes.",
        }

    spent = sum_for_period(user_id, "expense", start, as_of)
    elapsed_days = max(elapsed_days, 1)
    avg_daily = spent // elapsed_days
    projected = spent + (avg_daily * remaining_days)

    db = get_db()
    history = db.execute(
        """
        SELECT strftime('%Y', transaction_date) AS y, strftime('%m', transaction_date) AS m,
               SUM(amount_paise) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense' AND transaction_date < ?
        GROUP BY y, m
        HAVING COUNT(*) >= 3
        ORDER BY y DESC, m DESC
        LIMIT 6
        """,
        (user_id, start),
    ).fetchall()

    historical_avg = None
    blended = projected
    explanation = (
        f"Spent so far this month: {serialize_money(spent)['formatted']} over {elapsed_days} elapsed day(s). "
        f"Average daily expense = {serialize_money(avg_daily)['formatted']}. "
        f"Projected remaining spend = average daily × {remaining_days} remaining day(s). "
        f"Estimated month-end total = spent so far + remaining spend."
    )

    if history:
        totals = [int(row["total"]) for row in history]
        historical_avg = sum(totals) // len(totals)
        blended = (projected + historical_avg) // 2
        explanation += (
            f" A second check uses the average of {len(history)} earlier month(s) "
            f"({serialize_money(historical_avg)['formatted']}) and blends it equally with the current run-rate."
        )

    total_budget = db.execute(
        """
        SELECT COALESCE(SUM(monthly_limit_paise), 0) AS total
        FROM budgets
        WHERE user_id = ? AND year = ? AND month = ?
        """,
        (user_id, year, month),
    ).fetchone()["total"]

    sufficient = spent > 0 or bool(history)
    if not sufficient:
        return {
            "year": year,
            "month": month,
            "sufficient_data": False,
            "message": "Add a few expense transactions this month to generate a baseline estimate.",
            "method": "baseline_average_daily_run_rate",
            "spent_so_far": serialize_money(0),
            "elapsed_days": elapsed_days,
            "days_in_month": days_in_month,
            "remaining_days": remaining_days,
            "disclaimer": "This is a simple arithmetic estimate, not a trained predictive model.",
        }

    vs_budget = None
    if total_budget:
        vs_budget = {
            "budget": serialize_money(total_budget),
            "projected": serialize_money(blended),
            "difference": serialize_money(total_budget - blended),
            "over_budget": blended > total_budget,
        }

    return {
        "year": year,
        "month": month,
        "sufficient_data": True,
        "method": "baseline_average_daily_run_rate",
        "spent_so_far": serialize_money(spent),
        "average_daily": serialize_money(avg_daily),
        "elapsed_days": elapsed_days,
        "days_in_month": days_in_month,
        "remaining_days": remaining_days,
        "projected_month_end": serialize_money(projected),
        "historical_monthly_average": serialize_money(historical_avg) if historical_avg is not None else None,
        "blended_estimate": serialize_money(blended),
        "budget_comparison": vs_budget,
        "explanation": explanation,
        "disclaimer": (
            "This is a transparent baseline estimate using average daily spending. "
            "It is not a guarantee and is not a machine-learning model."
        ),
    }
