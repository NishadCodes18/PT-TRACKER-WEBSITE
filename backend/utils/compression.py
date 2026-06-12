"""Compression utilities for responses."""
from functools import wraps
from flask import request, make_response
import gzip
import io


def gzip_response(f):
    """Decorator to gzip compress responses."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        response = make_response(f(*args, **kwargs))

        # Only compress if client accepts gzip
        accept_encoding = request.headers.get('Accept-Encoding', '')
        if 'gzip' not in accept_encoding.lower():
            return response

        # Only compress text-based responses
        content_type = response.headers.get('Content-Type', '')
        if not any(ct in content_type.lower() for ct in ['text', 'json', 'javascript', 'css']):
            return response

        # Don't compress already encoded content
        if response.headers.get('Content-Encoding'):
            return response

        # Don't compress small responses (not worth it)
        if len(response.get_data()) < 500:
            return response

        # Compress the response
        gzip_buffer = io.BytesIO()
        with gzip.GzipFile(mode='wb', fileobj=gzip_buffer, compresslevel=6) as gzip_file:
            gzip_file.write(response.get_data())

        response.set_data(gzip_buffer.getvalue())
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Content-Length'] = len(response.get_data())
        response.headers['Vary'] = 'Accept-Encoding'

        return response

    return wrapper
