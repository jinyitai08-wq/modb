import signal
import multiprocessing

bind = "0.0.0.0:5000"
workers = min(2, multiprocessing.cpu_count())
threads = 4
timeout = 120
keepalive = 5
worker_class = "gthread"
accesslog = "-"
errorlog = "-"
loglevel = "info"
preload_app = False
graceful_timeout = 10
max_requests = 1000
max_requests_jitter = 50


def on_starting(server):
    signal.signal(signal.SIGWINCH, signal.SIG_IGN)


def post_fork(server, worker):
    signal.signal(signal.SIGWINCH, signal.SIG_IGN)
