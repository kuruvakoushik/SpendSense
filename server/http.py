"""Consistent JSON responses."""

from __future__ import annotations

from flask import jsonify


def ok(data=None, status: int = 200):
    return jsonify({"success": True, "data": data, "error": None}), status


def fail(message: str, status: int = 400, code: str = "invalid_request", details=None):
    payload = {"code": code, "message": message}
    if details:
        payload["details"] = details
    return jsonify({"success": False, "data": None, "error": payload}), status
