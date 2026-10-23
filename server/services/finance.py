"""Financial calculations using integer paise."""

from __future__ import annotations

import calendar
from datetime import date

from server.database import get_db
from server.validators import format_inr_from_paise, paise_to_rupees


def month_bounds(year: int, month: int) -> tuple[str, str]:
    last_day = calendar.monthrange(year, month)[1]
    return f"{year:04d}-{month:02d}-01", f"{year:04d}-{month:02d}-{last_day:02d}"


def serialize_money(paise: int) -> dict:
    return {
        "paise": int(paise),
        "rupees": paise_to_rupees(paise),
        "formatted": format_inr_from_paise(paise),
    }


def sum_for_period(user_id: int, tx_type: str, start: str, end: str, category_id: int | None = None) -> int:
    db = get_db()
    sql = """
        SELECT COALESCE(SUM(amount_paise), 0) AS total
        FROM transactions
        WHERE user_id = ? AND type = ? AND transaction_date >= ? AND transaction_date <= ?
    """
    params: list = [user_id, tx_type, start, end]
    if category_id is not None:
        sql += " AND category_id = ?"
        params.append(category_id)
    row = db.execute(sql, params).fetchone()
    return int(row["total"])


def category_owned(user_id: int, category_id: int, expected_type: str | None = None):
    db = get_db()
    row = db.execute(
        "SELECT * FROM categories WHERE id = ? AND user_id = ?",
        (category_id, user_id),
    ).fetchone()
    if row is None:
        return None
    if expected_type and row["type"] != expected_type:
        return None
    return row


def serialize_transaction(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "category_id": row["category_id"],
        "category_name": row["category_name"] if "category_name" in row.keys() else None,
        "category_color": row["category_color"] if "category_color" in row.keys() else None,
        "category_icon": row["category_icon"] if "category_icon" in row.keys() else None,
        "type": row["type"],
        "amount": serialize_money(row["amount_paise"]),
        "description": row["description"],
        "transaction_date": row["transaction_date"],
        "payment_method": row["payment_method"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def serialize_category(row) -> dict:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "type": row["type"],
        "color": row["color"],
        "icon": row["icon"],
        "is_system": bool(row["is_system"]),
        "created_at": row["created_at"],
    }


def serialize_budget(row, spent_paise: int) -> dict:
    limit_paise = int(row["monthly_limit_paise"])
    remaining = limit_paise - spent_paise
    utilization = round((spent_paise / limit_paise) * 100, 1) if limit_paise else 0
    status = "ok"
    if utilization >= 100:
        status = "over"
    elif utilization >= 80:
        status = "warning"
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "category_id": row["category_id"],
        "category_name": row["category_name"] if "category_name" in row.keys() else None,
        "category_color": row["category_color"] if "category_color" in row.keys() else None,
        "month": row["month"],
        "year": row["year"],
        "limit": serialize_money(limit_paise),
        "spent": serialize_money(spent_paise),
        "remaining": serialize_money(remaining),
        "utilization_percent": utilization,
        "status": status,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def budget_spent(user_id: int, category_id: int, year: int, month: int) -> int:
    start, end = month_bounds(year, month)
    return sum_for_period(user_id, "expense", start, end, category_id)


def dashboard_summary(user_id: int, year: int, month: int) -> dict:
    start, end = month_bounds(year, month)
    income = sum_for_period(user_id, "income", start, end)
    expenses = sum_for_period(user_id, "expense", start, end)
    net = income - expenses
    savings_rate = round((net / income) * 100, 1) if income > 0 else None

    db = get_db()
    breakdown = db.execute(
        """
        SELECT c.id, c.name, c.color, c.icon, COALESCE(SUM(t.amount_paise), 0) AS total
        FROM categories c
        LEFT JOIN transactions t
          ON t.category_id = c.id
         AND t.user_id = ?
         AND t.type = 'expense'
         AND t.transaction_date >= ?
         AND t.transaction_date <= ?
        WHERE c.user_id = ? AND c.type = 'expense'
        GROUP BY c.id
        HAVING total > 0
        ORDER BY total DESC
        """,
        (user_id, start, end, user_id),
    ).fetchall()

    budgets = db.execute(
        """
        SELECT b.*, c.name AS category_name, c.color AS category_color
        FROM budgets b
        JOIN categories c ON c.id = b.category_id
        WHERE b.user_id = ? AND b.year = ? AND b.month = ?
        ORDER BY c.name
        """,
        (user_id, year, month),
    ).fetchall()

    budget_rows = [serialize_budget(row, budget_spent(user_id, row["category_id"], year, month)) for row in budgets]

    return {
        "year": year,
        "month": month,
        "period_start": start,
        "period_end": end,
        "income": serialize_money(income),
        "expenses": serialize_money(expenses),
        "net": serialize_money(net),
        "savings_rate": savings_rate,
        "expense_breakdown": [
            {
                "category_id": row["id"],
                "name": row["name"],
                "color": row["color"],
                "icon": row["icon"],
                "total": serialize_money(row["total"]),
            }
            for row in breakdown
        ],
        "budgets": budget_rows,
        "has_transactions": bool(
            db.execute(
                "SELECT 1 FROM transactions WHERE user_id = ? LIMIT 1",
                (user_id,),
            ).fetchone()
        ),
    }


def recent_transactions(user_id: int, limit: int = 8) -> list[dict]:
    db = get_db()
    rows = db.execute(
        """
        SELECT t.*, c.name AS category_name, c.color AS category_color, c.icon AS category_icon
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ?
        ORDER BY t.transaction_date DESC, t.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [serialize_transaction(row) for row in rows]


def analytics_overview(user_id: int, start: str, end: str) -> dict:
    income = sum_for_period(user_id, "income", start, end)
    expenses = sum_for_period(user_id, "expense", start, end)
    db = get_db()
    daily = db.execute(
        """
        SELECT transaction_date, COALESCE(SUM(amount_paise), 0) AS total
        FROM transactions
        WHERE user_id = ? AND type = 'expense'
          AND transaction_date >= ? AND transaction_date <= ?
        GROUP BY transaction_date
        ORDER BY transaction_date
        """,
        (user_id, start, end),
    ).fetchall()
    categories = db.execute(
        """
        SELECT c.name, c.color, COALESCE(SUM(t.amount_paise), 0) AS total
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.user_id = ? AND t.type = 'expense'
          AND t.transaction_date >= ? AND t.transaction_date <= ?
        GROUP BY c.id
        ORDER BY total DESC
        """,
        (user_id, start, end),
    ).fetchall()
    return {
        "start": start,
        "end": end,
        "income": serialize_money(income),
        "expenses": serialize_money(expenses),
        "net": serialize_money(income - expenses),
        "daily_expenses": [
            {"date": row["transaction_date"], "total": serialize_money(row["total"])} for row in daily
        ],
        "category_breakdown": [
            {"name": row["name"], "color": row["color"], "total": serialize_money(row["total"])}
            for row in categories
        ],
    }


def monthly_trends(user_id: int, months: int = 6, end_year: int | None = None, end_month: int | None = None) -> list[dict]:
    today = date.today()
    year = end_year or today.year
    month = end_month or today.month
    points = []
    for _ in range(months):
        start, end = month_bounds(year, month)
        income = sum_for_period(user_id, "income", start, end)
        expenses = sum_for_period(user_id, "expense", start, end)
        points.append(
            {
                "year": year,
                "month": month,
                "label": f"{calendar.month_abbr[month]} {year}",
                "income": serialize_money(income),
                "expenses": serialize_money(expenses),
                "net": serialize_money(income - expenses),
            }
        )
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    points.reverse()
    return points


def insert_demo_data(user_id: int) -> int:
    """Insert labeled sample transactions for first-time exploration. Never silent."""
    db = get_db()
    cats = {
        row["name"]: row["id"]
        for row in db.execute("SELECT id, name FROM categories WHERE user_id = ?", (user_id,)).fetchall()
    }
    today = date.today()
    start, _ = month_bounds(today.year, today.month)
    samples = [
        ("Salary", "income", 5500000, "Monthly salary", start, "Net Banking"),
        ("Freelance", "income", 1200000, "Weekend freelance project", today.replace(day=min(8, today.day)).isoformat(), "UPI"),
        ("Food", "expense", 24500, "Groceries", today.replace(day=min(3, today.day)).isoformat(), "UPI"),
        ("Food", "expense", 8700, "Lunch with classmates", today.replace(day=min(6, today.day)).isoformat(), "UPI"),
        ("Transport", "expense", 15000, "Metro and auto", today.replace(day=min(5, today.day)).isoformat(), "UPI"),
        ("Education", "expense", 49900, "Online course", today.replace(day=min(4, today.day)).isoformat(), "Card"),
        ("Bills", "expense", 129900, "Mobile and broadband", today.replace(day=min(2, today.day)).isoformat(), "UPI"),
        ("Entertainment", "expense", 39900, "Movie night", today.replace(day=min(9, today.day)).isoformat(), "Card"),
        ("Shopping", "expense", 189900, "Stationery and clothes", today.replace(day=min(11, today.day)).isoformat(), "Card"),
        ("Healthcare", "expense", 65000, "Pharmacy", today.replace(day=min(7, today.day)).isoformat(), "Cash"),
    ]
    count = 0
    for name, tx_type, paise, desc, tx_date, method in samples:
        category_id = cats.get(name)
        if not category_id:
            continue
        if tx_date > today.isoformat():
            tx_date = today.isoformat()
        db.execute(
            """
            INSERT INTO transactions (
                user_id, category_id, type, amount_paise, description, transaction_date, payment_method
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (user_id, category_id, tx_type, paise, desc, tx_date, method),
        )
        count += 1

    food_id = cats.get("Food")
    if food_id:
        db.execute(
            """
            INSERT OR IGNORE INTO budgets (user_id, category_id, monthly_limit_paise, month, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, food_id, 800000, today.month, today.year),
        )
    bills_id = cats.get("Bills")
    if bills_id:
        db.execute(
            """
            INSERT OR IGNORE INTO budgets (user_id, category_id, monthly_limit_paise, month, year)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, bills_id, 200000, today.month, today.year),
        )
    db.commit()
    return count
