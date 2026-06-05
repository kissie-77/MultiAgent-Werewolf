# ─── 阶段 1：依赖安装 ─────────────────────────────────────────────────────
FROM python:3.10-slim AS builder

WORKDIR /build

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# 只复制依赖声明文件，利用 Docker 层缓存
COPY pyproject.toml uv.lock* ./

# 安装运行时依赖到固定路径（不含 dev/test/docs 组）
RUN uv sync --frozen --no-dev --no-group test --no-group docs \
    --python python3.10 \
    --compile-bytecode \
    && uv export --frozen --no-dev --no-group test --no-group docs \
       --format requirements-txt > /build/requirements.txt

# ─── 阶段 2：运行时镜像 ───────────────────────────────────────────────────
FROM python:3.10-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

# 从 builder 复制 venv（比重新 pip install 快）
COPY --from=builder /build/.venv /app/.venv
ENV PATH="/app/venv/bin:$PATH"

# 复制源码
COPY src/ ./src/
COPY configs/ ./configs/

# 创建非 root 用户
RUN useradd --no-create-home --no-log-init --uid 1000 appuser \
    && mkdir -p artifacts/alerts \
    && chown -R appuser:appuser /app

USER appuser

# 健康检查（依赖 /ready 端点）
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; r=urllib.request.urlopen('http://localhost:8000/ready',timeout=5); exit(0 if r.status==200 else 1)" || exit 1

EXPOSE 8000

# 生产模式：使用 uvicorn 多 worker
CMD ["/app/.venv/bin/uvicorn", \
     "llm_werewolf.interface.api.app:create_app", \
     "--factory", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info"]
