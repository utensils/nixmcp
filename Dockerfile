FROM python:3.11-slim

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install the package and dependencies
RUN pip install --no-cache-dir -e .

# Pre-cache data during build
RUN echo "Running pre-cache to populate cache data..." && \
    python -m mcp_nixos --pre-cache

# Set environment variables to ensure clean exit
ENV PYTHONUNBUFFERED=1
ENV MCP_NIXOS_CLEANUP_ORPHANS=true
# Set low timeout values for all operations
ENV MCP_NIXOS_SHUTDOWN_TIMEOUT=0.1
ENV MCP_NIXOS_STARTUP_TIMEOUT=1.0

# Use tini as init system to handle signals properly
RUN apt-get update && apt-get install -y tini && rm -rf /var/lib/apt/lists/*

# Use tini as entrypoint for proper signal forwarding and zombie reaping
ENTRYPOINT ["/usr/bin/tini", "--"]

# Run the MCP server through the run.py wrapper for better termination handling
CMD ["python", "-m", "mcp_nixos.run"]

# Add signal handler to ensure container exits cleanly
STOPSIGNAL SIGTERM
