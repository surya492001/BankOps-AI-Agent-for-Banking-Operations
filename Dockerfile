FROM python:3.12-slim

# Hugging Face Spaces runs containers as uid 1000.
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# CPU-only torch keeps the image far smaller than the default CUDA build.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the embedding model at build time so start-up is fast.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

COPY --chown=user . .

# Demo defaults. Override DATABASE_URL to use Postgres instead of SQLite.
ENV DATABASE_URL="sqlite:////tmp/bankops.db?check_same_thread=false" \
    CHROMA_PATH=/tmp/chroma_db \
    BANKOPS_API_URL=http://127.0.0.1:8000

EXPOSE 7860
CMD ["bash", "start.sh"]
