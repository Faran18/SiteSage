# Official Playwright image - Chromium + all its system libraries are
# already baked in, so there's no `playwright install --with-deps` step
# needed at all (that step is what failed on Render's native buildpack,
# since it requires root/apt-get access that non-Docker PaaS builds don't
# grant). Version tag matches backend/requirements.txt's playwright==1.55.0.
FROM mcr.microsoft.com/playwright/python:v1.55.0-noble

WORKDIR /app

# Install CPU-only torch FIRST, before sentence-transformers pulls in the
# default CUDA-bundled build. The default PyPI torch wheel bundles ~1.5GB
# of NVIDIA GPU libraries that are dead weight on Render's CPU-only free
# instance - this installs the same torch version (2.13.0, matching what
# the earlier build log resolved) from PyTorch's CPU-only wheel index
# instead, so pip sees the requirement already satisfied later and skips
# re-installing the GPU version.
RUN pip install --no-cache-dir torch==2.13.0 --index-url https://download.pytorch.org/whl/cpu

# Copy just the requirements file first so this layer is cached and only
# re-runs when dependencies actually change, not on every code edit.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

# Now copy the rest of the backend source
COPY backend backend

EXPOSE 8000

# $PORT is Render's dynamically-injected port; 8000 is the fallback for
# running this locally via `docker run`.
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}"]