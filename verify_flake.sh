#!/bin/bash
# set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Cleaning previous artifacts ---"
rm -rf .venv/ dist/ result* # Remove old venv, dist, and build results

# --- 1. Flake Checks (Lint, Types, Unit Tests) ---
echo
echo "--- Running: nix flake check . ---"
# Run without timeouts - allow as much time as needed
nix --show-trace flake check .
echo "✅ nix flake check passed!"

# --- 2. Build the Default Package ---
echo
echo "--- Running: nix build . ---"
nix --show-trace build .
echo "✅ nix build passed! Package is in ./result"
ls -l result # Show the symlink

# --- 3. Setup Virtual Environment ---
echo
echo "--- Running: nix run .#setup ---"
nix --show-trace run .#setup
echo "✅ venv setup command finished."
if [ ! -d ".venv" ]; then
   echo "❌ Error: .venv directory not created!"
   exit 1
fi
echo ".venv directory exists."

# --- 4. Linting App ---
echo
echo "--- Running: nix run .#lint ---"
nix --show-trace run .#lint
echo "✅ Lint command finished."

# --- 5. Type Checking App ---
echo
echo "--- Running: nix run .#typecheck ---"
nix --show-trace run .#typecheck
echo "✅ Typecheck command finished."

# --- 6. Formatting App (Optional - Run if you want to apply formatting) ---
# echo
# echo "--- Running: nix run .#format ---"
# nix --show-trace run .#format
# echo "✅ Format command finished."

# --- 7. Testing Apps ---
echo
echo "--- Running: nix run .#tests (all tests) ---"
nix --show-trace run .#tests
echo "✅ All tests finished."

echo
echo "--- Running: nix run .#tests -- --unit ---"
nix --show-trace run .#tests -- --unit
echo "✅ Unit tests finished."

echo
echo "--- Running: nix run .#tests -- --integration ---"
nix --show-trace run .#tests -- --integration
echo "✅ Integration tests finished."

# --- 8. Build Distribution App ---
echo
echo "--- Running: nix run .#build ---"
nix --show-trace run .#build
echo "✅ Build command finished."
if [ ! -d "dist" ]; then
   echo "❌ Error: dist directory not created!"
   exit 1
fi
echo "dist directory exists:"
ls -l dist/

# --- 9. Running the Server App (Briefly) ---
echo
echo "--- Running: nix run . (server start test) ---"
# Run in background, wait a moment, check if running, then kill
(nix --show-trace run . &)
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID (waiting 5s)"
sleep 5
if ps -p $SERVER_PID >/dev/null; then
   echo "✅ Server process seems to be running."
   echo "Attempting to stop server (PID: $SERVER_PID)..."
   kill $SERVER_PID
   sleep 2 # Give it a moment to exit
   if ps -p $SERVER_PID >/dev/null; then
      echo "⚠️ Server might still be running, killing forcefully."
      kill -9 $SERVER_PID
   else
      echo "✅ Server stopped gracefully."
   fi
else
   echo "❌ Error: Server process did not start or exited prematurely."
   # Try to get exit code if possible
   wait $SERVER_PID || echo "(Server exited with code $?)"
   exit 1
fi

# --- 10. Test Entering Dev Shell (Non-interactive) ---
echo
echo "--- Running: nix develop -c echo 'Entered Dev Shell' ---"
nix --show-trace develop -c echo "✅ Successfully entered and exited dev shell."

echo
echo "--- All Verification Commands Completed ---"
