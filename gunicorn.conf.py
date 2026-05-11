"""Gunicorn 프로덕션 설정.

workers = 4: CPU 코어 수 × 2 권장
worker_class: uvicorn의 async worker 사용
"""

bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
loglevel = "info"
keepalive = 5
graceful_timeout = 30
timeout = 60
