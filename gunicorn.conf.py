"""
Gunicorn production configuration.
Handles: worker count, timeouts, logging, graceful shutdown.

IMPORTANT — Scheduler & Telegram bot run in ONE worker only.
We use 1 worker + threads to avoid duplicate scheduled jobs.
For high traffic, use a separate worker process with --preload
and a distributed lock (Redis). For this project, 1 worker is enough.
"""
import os
import multiprocessing

# ── Binding ───────────────────────────────────────────────────────────────────
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# ── Workers ───────────────────────────────────────────────────────────────────
# 1 worker = scheduler + telegram bot run exactly once (no duplicate jobs)
# Use threads for concurrency instead of multiple workers
workers = 1
threads = 4
worker_class = "gthread"

# ── Timeouts ──────────────────────────────────────────────────────────────────
timeout = 120          # AI calls can take up to 2 minutes
graceful_timeout = 30  # time to finish in-flight requests on shutdown
keepalive = 5

# ── Logging ───────────────────────────────────────────────────────────────────
loglevel = os.environ.get("LOG_LEVEL", "info")
accesslog = "-"   # stdout
errorlog  = "-"   # stderr
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Process ───────────────────────────────────────────────────────────────────
preload_app = True     # load app once, share across threads (saves memory)
daemon = False         # Docker/systemd manages the process
pidfile = None

# ── Hooks ─────────────────────────────────────────────────────────────────────
def on_starting(server):
    server.log.info("🚀 Gunicorn starting — بوست سوشال")

def worker_exit(server, worker):
    server.log.info(f"Worker {worker.pid} exited")
