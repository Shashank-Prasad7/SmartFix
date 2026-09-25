FROM node:24-alpine AS frontend
WORKDIR /build
RUN npm install -g pnpm@11.19.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml frontend/vite.config.mjs frontend/tsconfig.json frontend/index.html ./
COPY frontend/src ./src
COPY frontend/public ./public
RUN pnpm install --frozen-lockfile --store-dir /build/.pnpm-store && pnpm exec tsc --noEmit && pnpm exec vite build --config vite.config.mjs --configLoader runner

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app PORT=8000 HOST=0.0.0.0

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY src /app/theme2/src
COPY data/official/student_kit /app/theme2/data/official/student_kit
COPY data/fixtures /app/theme2/data/fixtures
COPY --from=frontend /static/app /app/theme2/static/app
RUN useradd --create-home prism && mkdir -p /app/theme2/.runtime && chown -R prism:prism /app/theme2
USER prism

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1
CMD ["python", "-m", "uvicorn", "theme2.src.api:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
