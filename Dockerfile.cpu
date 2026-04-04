FROM python:3.11-slim

# Prevent writing .pyc files and holding/buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system deps as needed (git, build-essential, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    libopenblas-dev \
    git \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Speed up C++ compilation massively and enable OpenBLAS for CPU acceleration
ENV CMAKE_BUILD_PARALLEL_LEVEL=4
ENV CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DGGML_NATIVE=OFF -DLLAMA_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DLLAMA_AVX=ON -DLLAMA_AVX2=ON -DLLAMA_FMA=ON -DLLAMA_F16C=ON"
ENV OMP_NUM_THREADS=8
ENV OPENBLAS_NUM_THREADS=8

# Set up a new user named "user" with user ID 1000
# Hugging Face Spaces strictly runs containers as user 1000
RUN useradd -m -u 1000 user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Change working directory to the user's application path
WORKDIR $HOME/app

# Copy requirements and transfer ownership to the user
COPY --chown=user:user requirements.txt .

# Switch to the new user before installing dependencies
USER user

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY --chown=user:user . .

# Set HF_HOME so huggingface_hub (used by llama_cpp) caches in a writable directory
ENV HF_HOME=$HOME/.cache/huggingface

# Streamlit config (disable headless warnings, use Spaces default port 7860)
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_SERVER_PORT=7860
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_ENABLE_CORS=false
ENV STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=false

EXPOSE 7860

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=7860", "--server.address=0.0.0.0"]