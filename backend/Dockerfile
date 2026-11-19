FROM python:3.12-slim
WORKDIR /code
ENV PORT 8000
EXPOSE 8000
# Install dependencies and clean up in one layer
RUN apt-get update && \
   apt-get install -y --no-install-recommends \
   libmagic1 \
   libgl1 \
   libglib2.0-0 \
   libglx-mesa0 \
   libgomp1 \
   libreoffice \
   cmake \
   poppler-utils \
   tesseract-ocr \
   git && \
   apt-get clean && \
   rm -rf /var/lib/apt/lists/*

# Set LD_LIBRARY_PATH
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
# Copy requirements file and install Python dependencies
COPY requirements.txt constraints.txt /code/
# --no-cache-dir --upgrade 
RUN pip install --upgrade pip
# CPU-only PyTorch (no NVIDIA CUDA libraries); pinned so requirements.txt keeps it
RUN pip install --index-url https://download.pytorch.org/whl/cpu torch torchvision && \
   pip freeze | grep -iE '^(torch|torchvision)==' > /tmp/torch-cpu.txt
RUN pip install -r requirements.txt -c /tmp/torch-cpu.txt

# Embeddings use Vertex AI (EMBEDDING_MODEL=vertexai); no local MiniLM model is downloaded

RUN python -m nltk.downloader -d /usr/local/nltk_data punkt
RUN python -m nltk.downloader -d /usr/local/nltk_data averaged_perceptron_tagger

# Copy application code
COPY . /code

# Run as root to avoid volume permission issues in different environments
# RUN useradd -r appuser && chown -R appuser /code
# USER appuser

# Set command
CMD ["gunicorn", "score:app", "--workers", "2", "--threads", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "300"]
