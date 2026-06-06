"""Consistent JSON API responses."""
from flask import jsonify


def api_success(data=None, message=None, status=200, **extra):
    body = {'ok': True}
    if message:
        body['message'] = message
    if data is not None:
        body['data'] = data
    body.update(extra)
    return jsonify(body), status


def api_error(message, code='error', status=400, **extra):
    body = {'ok': False, 'error': message, 'code': code}
    body.update(extra)
    return jsonify(body), status
