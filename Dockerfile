FROM python:3.11-slim

# Prevent writing .pyc files and holding/buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install only minimal runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Expose pip-installed NVIDIA CUDA runtime .so files (libcudart.so.12, libcublas.so.12, etc.)
# to the Linux dynamic linker so llama_cpp can load them at startup.
ENV LD_LIBRARY_PATH="/home/user/.local/lib/python3.11/site-packages/nvidia/cuda_runtime/lib:\
/home/user/.local/lib/python3.11/site-packages/nvidia/cublas/lib:${LD_LIBRARY_PATH}"

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

# Install Python packages (llama-cpp-python pulls pre-built CUDA wheel - no compilation!)
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