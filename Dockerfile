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

# Run the MCP server
CMD ["python", "-m", "mcp_nixos"]
