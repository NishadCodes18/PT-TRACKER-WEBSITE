"""Gunicorn configuration for Render deployment."""
import multiprocessing
import os
import sys

bind = f"0.0.0.0:{os.environ.get('PORT', 5000)}"
workers = 3
threads = 2
worker_class = "sync"
worker_connections = 1000
timeout = 120
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 50

preload_app = True
daemon = False

loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

def worker_int(worker):
    """Handle worker interruption."""
    pass

def on_starting(server):
    """Called just before the master process is initialized."""
    print("=" * 60)
    print("GUNICORN STARTING")
    print(f"Binding to: {bind}")
    print(f"Workers: {workers}")
    print(f"Timeout: {timeout}s")
    print("=" * 60)

def when_ready(server):
    """Called just after the server is started."""
    print("=" * 60)
    print("✅ GUNICORN READY - Server is accepting connections")
    print("=" * 60)

def worker_abort(worker):
    """Called when a worker times out."""
    print(f"⚠ Worker {worker.pid} timed out")
    sys.stderr.flush()
    sys.stdout.flush()
