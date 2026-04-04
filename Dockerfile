FROM nvidia/cuda:12.3.2-devel-ubuntu22.04

# Prevent writing .pyc files and holding/buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Tell apt-get we are non-interactive to avoid hanging on tzdata dialogs
ENV DEBIAN_FRONTEND=noninteractive

# Install dependencies, Python 3.11, and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common wget git pkg-config cmake build-essential \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    python3.11 python3.11-venv python3.11-dev \
    && rm -rf /var/lib/apt/lists/*

# Symlink python3 and python to python3.11 cleanly
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Install pip securely directly to Python 3.11
RUN wget -qO get-pip.py https://bootstrap.pypa.io/get-pip.py \
    && python3.11 get-pip.py \
    && rm get-pip.py

# Speed up C++ compilation massively and enable CUDA for GPU acceleration
ENV CMAKE_BUILD_PARALLEL_LEVEL=4
ENV CMAKE_ARGS="-DGGML_CUDA=ON"

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
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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