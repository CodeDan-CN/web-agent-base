FROM registry.cn-beijing.aliyuncs.com/codedan_docker/python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8003

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip \
    && pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

COPY app.py .
COPY agents ./agents
COPY exception ./exception
COPY runtime ./runtime
COPY schema ./schema
COPY utils ./utils
COPY web ./web

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8003

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://127.0.0.1:{os.getenv(\"PORT\", \"8003\")}/health', timeout=3).read()"

CMD ["sh", "-c", "uvicorn app:app --host ${HOST:-0.0.0.0} --port ${PORT:-8003}"]
