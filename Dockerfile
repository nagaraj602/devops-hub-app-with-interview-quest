# ==========================================
# Stage 1: Build & Python Dependencies (Ubuntu Base)
# ==========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    gcc \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# Install dependencies into /install virtual environment
RUN python3 -m venv /install/venv && \
    /install/venv/bin/pip install --no-cache-dir -r requirements.txt

# ==========================================
# Stage 2: Final Production Runtime Image (Ubuntu Base)
# ==========================================
FROM ubuntu:24.04 AS runner

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/install/venv/bin:$PATH"

WORKDIR /app

# Install runtime system packages on Ubuntu
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    git \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python virtual environment from builder stage
COPY --from=builder /install/venv /install/venv

# Copy application source code, content, logs, and project documentation
COPY app/ /app/app/
COPY content/ /app/content/
COPY logs/ /app/logs/
COPY Project /app/Project
COPY README.md /app/README.md

# Environment Configuration
ENV PORT=8926
ENV HOST=0.0.0.0
ENV PYTHONUNBUFFERED=1

EXPOSE 8926

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8926/api/health || exit 1

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8926"]
