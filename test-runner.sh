#!/usr/bin/env bash
set -e

# Default test directory
TEST_DIR="tests/"
CLEAN_CACHE=true
VERBOSE="-v"
TEST_ARGS=""

# Function to clean cache directories
clean_cache() {
  echo "Cleaning cache directories before tests..."
  
  # Default cache location on macOS
  if [[ "$OSTYPE" == "darwin"* ]]; then
    CACHE_DIR="${HOME}/Library/Caches/mcp_nixos"
  # Default cache location on Linux
  elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    CACHE_DIR="${HOME}/.cache/mcp_nixos"
  # Fallback for other systems
  else
    CACHE_DIR="${HOME}/.cache/mcp_nixos"
  fi
  
  # Also check if MCP_NIXOS_CACHE_DIR is set
  if [[ -n "${MCP_NIXOS_CACHE_DIR}" ]]; then
    CACHE_DIR="${MCP_NIXOS_CACHE_DIR}"
  fi
  
  # Remove the cache directory if it exists
  if [[ -d "${CACHE_DIR}" ]]; then
    echo "Removing cache directory: ${CACHE_DIR}"
    rm -rf "${CACHE_DIR}"
  else
    echo "Cache directory not found: ${CACHE_DIR} (nothing to clean)"
  fi
  
  # Additional cleanup: remove any temporary test cache directories
  TMP_CACHE_DIRS=$(find /tmp -name "mcp_nixos_test_cache_*" -type d 2>/dev/null || echo "")
  if [[ -n "${TMP_CACHE_DIRS}" ]]; then
    echo "Removing temporary test cache directories:"
    echo "${TMP_CACHE_DIRS}"
    rm -rf ${TMP_CACHE_DIRS}
  fi
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-clean-cache)
      CLEAN_CACHE=false
      shift
      ;;
    --unit)
      # Run only unit tests (skip integration tests)
      TEST_ARGS="-k 'not integration'"
      shift
      ;;
    --integration)
      # Run only integration tests
      TEST_ARGS="-m integration"
      shift
      ;;
    --quiet)
      VERBOSE=""
      shift
      ;;
    *)
      # Assume this is a directory or file to test
      TEST_DIR="$1"
      shift
      ;;
  esac
done

# Clean cache if requested
if [[ "${CLEAN_CACHE}" == "true" ]]; then
  clean_cache
fi

# Verify dependencies are properly installed
echo "Verifying dependencies before running tests..."
python -m pip install -e .[dev]

# Run the tests based on arguments
if [ -n "$TEST_ARGS" ]; then
  echo "Running tests with args: ${TEST_ARGS}"
  python -m pytest ${TEST_DIR} ${VERBOSE} ${TEST_ARGS}
else
  echo "Running all tests..."
  python -m pytest ${TEST_DIR} ${VERBOSE}
fi

# Clean up after tests regardless of outcome
if [[ "${CLEAN_CACHE}" == "true" ]]; then
  clean_cache
fi
