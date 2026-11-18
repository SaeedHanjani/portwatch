# syntax=docker/dockerfile:1

# ---- build stage: install the package and its dependencies into /install ----
FROM python:3.12-slim AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir --prefix=/install .

# ---- runtime stage: only what is needed to run, as a non-root user ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN useradd --system --uid 10001 --no-create-home portwatch
COPY --from=builder /install /usr/local
USER portwatch
WORKDIR /app
EXPOSE 9877
ENTRYPOINT ["portwatch"]
CMD ["--help"]
