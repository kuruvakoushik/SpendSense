"""Rule-based unusual expense detection using median and MAD."""

from __future__ import annotations

import calendar
import statistics
from datetime import date

from server.database import get_db
from server.services.finance import (
    budget_spent,
    month_bounds,
    serialize_budget,
    serialize_money,
    serialize_transaction,
    sum_for_period,
)

MIN_HISTORY = 5
MODIFIED_Z_THRESHOLD = 3.5


def _modified_z(amount: int, history: list[int]) -> tuple[float | None, int, int]:
    median = int(statistics.median(history))
    deviations = [abs(value - median) for value in history]
    mad = int(statistics.median(deviations))
    if mad == 0:
        return None, median, mad
    score = (0.6745 * (amount - median)) / mad
    return score, median, mad


def detect_anomalies(user_id: int) -> dict:
    db = get_db()
    rows = db.execute(
        """
        SELECT t.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ? AND t.type = 'expense'
        ORDER BY t.transaction_date DESC, t.id DESC
        """,
        (user_id,),
    ).fetchall()

    flagged = []
    insufficient = False

    for row in rows:
        history_rows = db.execute(
            """
            SELECT amount_paise FROM transactions
            WHERE user_id = ? AND category_id = ? AND type = 'expense' AND id != ?
            """,
            (user_id, row["category_id"], row["id"]),
        ).fetchall()
        history = [int(item["amount_paise"]) for item in history_rows]
        if len(history) < MIN_HISTORY:
            insufficient = True
            continue

        amount = int(row["amount_paise"])
        score, median, mad = _modified_z(amount, history)
        reason = None
        if mad == 0:
            if median > 0 and amount >= median * 3:
                reason = (
                    f"{row['category_name']} expenses are usually {serialize_money(median)['formatted']}. "
                    f"This payment is at least 3× that typical amount."
                )
        elif score is not None and score > MODIFIED_Z_THRESHOLD and amount > median:
            reason = (
                f"Compared with {len(history)} earlier {row['category_name']} expenses "
                f"(typical amount {serialize_money(median)['formatted']}), this payment of "
                f"{serialize_money(amount)['formatted']} is unusually large "
                f"(robust z-score {score:.1f}, threshold {MODIFIED_Z_THRESHOLD})."
            )

        if reason:
            item = serialize_transaction(row)
            item["reason"] = reason
            item["typical_amount"] = serialize_money(median)
            item["sample_size"] = len(history)
            flagged.append(item)

    return {
        "method": "median_absolute_deviation",
        "minimum_history": MIN_HISTORY,
        "threshold": MODIFIED_Z_THRESHOLD,
        "disclaimer": (
            "An unusual amount is not necessarily fraudulent. It only means the payment "
            "differs substantially from this category's typical history."
        ),
        "flagged": flagged,
        "insufficient_history_note": (
            f"Some categories do not yet have enough history for comparison. "
            f"At least {MIN_HISTORY} earlier expenses in the same category are required."
            if insufficient
            else None
        ),
    }


def build_insights(user_id: int, year: int, month: int) -> list[dict]:
    insights: list[dict] = []
    db = get_db()
    start, end = month_bounds(year, month)
    prev_month = 12 if month == 1 else month - 1
    prev_year = year - 1 if month == 1 else year
    prev_start, prev_end = month_bounds(prev_year, prev_month)

    expenses = sum_for_period(user_id, "expense", start, end)
    income = sum_for_period(user_id, "income", start, end)
    prev_expenses = sum_for_period(user_id, "expense", prev_start, prev_end)
    prev_income = sum_for_period(user_id, "income", prev_start, prev_end)

    tx_count = db.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE user_id = ?",
        (user_id,),
    ).fetchone()["n"]
    if tx_count == 0:
        return [
            {
                "severity": "info",
                "title": "No transactions yet",
                "detail": "Add income and expenses to unlock budget tracking, charts, and spending insights.",
            }
        ]

    last_tx = db.execute(
        """
        SELECT transaction_date FROM transactions
        WHERE user_id = ? ORDER BY transaction_date DESC, id DESC LIMIT 1
        """,
        (user_id,),
    ).fetchone()
    if last_tx:
        last_date = date.fromisoformat(last_tx["transaction_date"])
        gap = (date.today() - last_date).days
        if gap >= 7:
            insights.append(
                {
                    "severity": "warning",
                    "title": "No recent activity",
                    "detail": f"The last recorded transaction was {gap} days ago ({last_tx['transaction_date']}).",
                }
            )

    budgets = db.execute(
        """
        SELECT b.*, c.name AS category_name, c.color AS category_color
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.user_id = ? AND b.year = ? AND b.month = ?
        """,
        (user_id, year, month),
    ).fetchall()
    for row in budgets:
        spent = budget_spent(user_id, row["category_id"], year, month)
        item = serialize_budget(row, spent)
        if item["status"] == "over":
            insights.append(
                {
                    "severity": "alert",
                    "title": f"{row['category_name']} is over budget",
                    "detail": (
                        f"Spent {item['spent']['formatted']} of {item['limit']['formatted']} "
                        f"({item['utilization_percent']}% utilized)."
                    ),
                }
            )
        elif item["status"] == "warning":
            insights.append(
                {
                    "severity": "warning",
                    "title": f"{row['category_name']} is nearing its budget",
                    "detail": (
                        f"Spending has reached {item['utilization_percent']}% of the "
                        f"{item['limit']['formatted']} monthly limit."
                    ),
                }
            )

    breakdown = db.execute(
        """
        SELECT c.name, SUM(t.amount_paise) AS total
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ? AND t.type = 'expense'
          AND t.transaction_date >= ? AND t.transaction_date <= ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, start, end),
    ).fetchall()
    if expenses > 0 and breakdown:
        top = breakdown[0]
        share = round((int(top["total"]) / expenses) * 100, 1)
        if share >= 40:
            insights.append(
                {
                    "severity": "info",
                    "title": f"{top['name']} is a large share of spending",
                    "detail": f"{top['name']} accounts for {share}% of expenses this month.",
                }
            )

        prev_by_name = {
            row["name"]: int(row["total"])
            for row in db.execute(
                """
                SELECT c.name, SUM(t.amount_paise) AS total
                FROM transactions t
                JOIN categories c ON c.id = t.category_id
                WHERE t.user_id = ? AND t.type = 'expense'
                  AND t.transaction_date >= ? AND t.transaction_date <= ?
                GROUP BY c.id
                """,
                (user_id, prev_start, prev_end),
            ).fetchall()
        }
        if prev_by_name:
            for row in breakdown:
                previous = prev_by_name.get(row["name"])
                current = int(row["total"])
                if previous and previous > 0 and current >= int(previous * 1.4) and current - previous >= 20000:
                    growth = round(((current - previous) / previous) * 100)
                    insights.append(
                        {
                            "severity": "warning",
                            "title": f"{row['name']} spending rose versus last month",
                            "detail": f"{row['name']} is about {growth}% higher than {prev_start[:7]}.",
                        }
                    )

    if prev_expenses > 0:
        change = round(((expenses - prev_expenses) / prev_expenses) * 100)
        if abs(change) >= 25:
            direction = "higher" if change > 0 else "lower"
            insights.append(
                {
                    "severity": "info",
                    "title": "Monthly expenses shifted",
                    "detail": f"Total expenses are {abs(change)}% {direction} than the previous month.",
                }
            )
    else:
        insights.append(
            {
                "severity": "info",
                "title": "Limited history for comparison",
                "detail": "Record another month of transactions to compare spending with the previous period.",
            }
        )

    if prev_income > 0:
        change = round(((income - prev_income) / prev_income) * 100)
        if abs(change) >= 25:
            direction = "higher" if change > 0 else "lower"
            insights.append(
                {
                    "severity": "info",
                    "title": "Income changed versus last month",
                    "detail": f"Income is {abs(change)}% {direction} than the previous month.",
                }
            )

    today = date.today()
    if year == today.year and month == today.month and expenses > 0:
        elapsed = max(today.day, 1)
        days = calendar.monthrange(year, month)[1]
        expected_pace = int(expenses * days / elapsed)
        total_budget = db.execute(
            """
            SELECT COALESCE(SUM(monthly_limit_paise), 0) AS total
            FROM budgets WHERE user_id = ? AND year = ? AND month = ?
            """,
            (user_id, year, month),
        ).fetchone()["total"]
        if total_budget and expected_pace > total_budget:
            insights.append(
                {
                    "severity": "warning",
                    "title": "Spending is ahead of pace",
                    "detail": (
                        "If the current daily average continues, month-end expenses may exceed "
                        "the combined category budgets for this month."
                    ),
                }
            )

    if not insights:
        insights.append(
            {
                "severity": "info",
                "title": "Spending looks steady",
                "detail": "No budget overruns or large month-over-month shifts were detected for this period.",
            }
        )
    return insights
