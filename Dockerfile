# ================================================================================
# Agentic AI Tutor - Dockerfile
# ================================================================================
# This Dockerfile creates a containerized environment for the Agentic AI system
# with document processing (PDF/DOCX/ODT), vision capabilities, and voice I/O.
#
# Base Image: python:3.9-slim for minimal footprint
# ================================================================================

FROM python:3.9-slim

WORKDIR /app

# ================================================================================
# Layer 1: Copy requirements first (leverages Docker cache)
# ================================================================================
# By copying requirements.txt separately, we can cache the pip install layer.
# This speeds up rebuilds when only source code changes.
COPY agentic_system/requirements.txt ./agentic_system/

# ================================================================================
# Layer 2: Install system dependencies
# ================================================================================
# Database: libpq-dev (PostgreSQL client libraries)
# Document processing: tesseract-ocr (OCR for images)
# Multi-language support: nodejs, golang, rust, gcc/g++
# Cleanup: Remove apt cache to reduce image size
RUN apt-get update && apt-get install -y \
    libpq-dev \
    tesseract-ocr \
    tesseract-ocr-eng \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js (for JavaScript)
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Go (for Go)
RUN curl -OL https://golang.org/dl/go1.21.5.linux-amd64.tar.gz \
    && tar -C /usr/local -xzf go1.21.5.linux-amd64.tar.gz \
    && rm go1.21.5.linux-amd64.tar.gz
ENV PATH=$PATH:/usr/local/go/bin

# Install Rust (for Rust)
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Install GCC/G++ (for C/C++)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# ================================================================================
# Layer 3: Install Python dependencies
# ================================================================================
# Install from requirements.txt with no cache to reduce image size
RUN pip install --no-cache-dir -r agentic_system/requirements.txt

# ================================================================================
# Layer 4: Copy application source code
# ================================================================================
# Copy only necessary files to keep image lean
COPY agentic_system/src ./agentic_system/src
COPY app.py .
COPY .env .

# ================================================================================
# Layer 5: Set environment variables
# ================================================================================
# PYTHONPATH: Ensures Python can import from agentic_system module
ENV PYTHONPATH=/app

# ================================================================================
# Entrypoint: Run Streamlit application
# ================================================================================
# Expose port 8501 for Streamlit UI
# Command runs the Streamlit app with default configuration
EXPOSE 8501
CMD ["streamlit", "run", "app.py"]
