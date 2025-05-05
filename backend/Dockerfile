# FastAPI Backend Dockerfile
FROM python:3.11.7

# Set working directory
WORKDIR /app

# Install build tools & system-level dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev \
    libbz2-dev \
    libreadline-dev \
    libsqlite3-dev \
    libssl-dev \
    curl \
    libncurses5-dev \
    libncursesw5-dev \
    liblzma-dev \
    xz-utils \
    git \
    python3-dev \
    cmake \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Install Cython using pip
RUN pip install --upgrade pip && pip install cython

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY . .

# Expose FastAPI port
EXPOSE 8000

# Run FastAPI server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
