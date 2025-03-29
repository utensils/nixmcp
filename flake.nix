{
  description = "MCP-NixOS - Model Context Protocol server for NixOS and Home Manager resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    devshell.url = "github:numtide/devshell";
  };

  outputs = { self, nixpkgs, flake-utils, devshell }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs {
          inherit system;
          overlays = [ devshell.overlays.default ];
        };

        pythonVersion = "311";
        python = pkgs."python${pythonVersion}";
        ps = pkgs."python${pythonVersion}Packages";

        pythonForVenv = python.withPackages (p: with p; [ ]);

        setupVenvScript = pkgs.writeShellScriptBin "setup-venv" ''
          set -e
          echo "--- Setting up Python virtual environment ---"

          if [ ! -f "requirements.txt" ]; then
            echo "Warning: requirements.txt not found. Creating an empty one."
            touch requirements.txt
          fi

          if [ ! -d ".venv" ]; then
            echo "Creating Python virtual environment in ./.venv ..."
            ${pythonForVenv}/bin/python -m venv .venv
          else
            echo "Virtual environment ./.venv already exists."
          fi

          source .venv/bin/activate

          echo "Upgrading pip, setuptools, wheel in venv..."
          if command -v uv >/dev/null 2>&1; then
            uv pip install --upgrade pip setuptools wheel
          else
            python -m pip install --upgrade pip setuptools wheel
          fi

          echo "Installing dependencies from requirements.txt..."
          if command -v uv >/dev/null 2>&1; then
            echo "(Using uv)"
            uv pip install -r requirements.txt
          else
            echo "(Using pip)"
            python -m pip install -r requirements.txt
          fi

          if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
            echo "Installing project in editable mode..."
            if command -v uv >/dev/null 2>&1; then
              uv pip install -e .
            else
              python -m pip install -e .
            fi
          else
             echo "No setup.py or pyproject.toml found, skipping editable install."
          fi

           echo "✓ Python environment setup complete in ./.venv"
           echo "---------------------------------------------"
        '';

      in
      {
        devShells.default = pkgs.devshell.mkShell {
          name = "mcp-nixos";
          motd = ''
            Entering MCP-NixOS Dev Environment...
            Python: ${python.version}
            Nix:    ${pkgs.nix}/bin/nix --version
          '';
          env = [
            { name = "PYTHONPATH"; value = "$PWD"; }
            { name = "MCP_NIXOS_ENV"; value = "development"; }
          ];
          packages = with pkgs; [
            # Python & Build Tools
            pythonForVenv
            uv # Faster pip alternative
            ps.build
            ps.twine

            # Linters & Formatters
            ps.black
            ps.flake8
            # Standalone pyright package
            pyright # <--- CORRECTED REFERENCE

            # Testing
            ps.pytest
            ps."pytest-cov"
            # ps.pytest-asyncio # Usually installed via pip/uv into venv

            # Nix & Git
            nix
            nixos-option
            git
          ];
          commands = [
            {
              name = "setup";
              category = "environment";
              help = "Set up/update Python virtual environment (.venv) and install dependencies";
              command = "${setupVenvScript}/bin/setup-venv";
            }
            {
              name = "run";
              category = "server";
              help = "Run the MCP-NixOS server";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi
                if ! python -c "import mcp_nixos" &>/dev/null; then
                   echo "Editable install 'mcp_nixos' not found. Running setup..."
                   ${setupVenvScript}/bin/setup-venv
                   source .venv/bin/activate
                fi
                echo "Starting MCP-NixOS server (python -m mcp_nixos)..."
                python -m mcp_nixos
              '';
            }
            {
              name = "run-tests";
              category = "testing";
              help = "Run tests with pytest [--no-coverage]";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then
                  echo "Activating venv..."
                  source .venv/bin/activate
                fi
                COVERAGE_ARGS="--cov=mcp_nixos --cov-report=term --cov-report=html --cov-report=xml"
                if [ $# -gt 0 ] && [ "$1" = "--no-coverage" ]; then
                  COVERAGE_ARGS=""
                  echo "Running without coverage reporting..."
                  shift
                fi
                SOURCE_DIR="mcp_nixos"
                echo "Running tests..."
                pytest tests/ -v $COVERAGE_ARGS "$@"
                if [ -n "$COVERAGE_ARGS" ] && echo "$COVERAGE_ARGS" | grep -q 'html'; then
                  echo "✅ Coverage report generated. HTML report available in htmlcov/"
                elif [ -n "$COVERAGE_ARGS" ]; then
                   echo "✅ Coverage report generated."
                fi
              '';
            }
            {
              name = "loc";
              category = "development";
              help = "Count lines of code in the project";
              command = ''
                echo "=== MCP-NixOS Lines of Code Statistics ==="
                SRC_LINES=$(find ./mcp_nixos -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                TEST_LINES=$(find ./tests -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                # Corrected path pruning for loc command
                CONFIG_LINES=$(find . -path './.venv' -prune -o -path './.mypy_cache' -prune -o -path './htmlcov' -prune -o -path './.direnv' -prune -o -path './result' -prune -o -path './.git' -prune -o -type f \( -name '*.json' -o -name '*.toml' -o -name '*.ini' -o -name '*.yml' -o -name '*.yaml' -o -name '*.nix' -o -name '*.lock' -o -name '*.md' -o -name '*.rules' -o -name '*.hints' -o -name '*.in' \) -print | xargs wc -l | tail -n 1 | awk '{print $1}')
                TOTAL_PYTHON=$((SRC_LINES + TEST_LINES))
                echo "Source code (mcp_nixos directory): $SRC_LINES lines"
                echo "Test code (tests directory): $TEST_LINES lines"
                echo "Configuration files: $CONFIG_LINES lines"
                echo "Total Python code: $TOTAL_PYTHON lines"
                if [ "$SRC_LINES" -gt 0 ]; then
                  RATIO=$(echo "scale=2; $TEST_LINES / $SRC_LINES" | bc)
                  echo "Test to code ratio: $RATIO:1"
                fi
              '';
            }
            {
              name = "lint";
              category = "development";
              help = "Lint code with Black (check) and Flake8";
              command = ''
                echo "--- Checking formatting with Black ---"
                black --check mcp_nixos/ tests/
                echo "--- Running Flake8 linter ---"
                flake8 mcp_nixos/ tests/
              '';
            }
            {
              name = "typecheck"; # Added a dedicated command for clarity
              category = "development";
              help = "Run pyright type checker";
              command = "pyright"; # Direct command
            }
            {
              name = "format";
              category = "development";
              help = "Format code with Black";
              command = ''
                echo "--- Formatting code with Black ---"
                black mcp_nixos/ tests/
                echo "✅ Code formatted"
              '';
            }
            {
              name = "build";
              category = "distribution";
              help = "Build package distributions (sdist and wheel)";
              command = ''
                 echo "--- Building package ---"
                rm -rf dist/ build/ *.egg-info
                python -m build
                echo "✅ Build complete in dist/"
              '';
            }
            {
              name = "publish";
              category = "distribution";
              help = "Upload package distribution to PyPI (requires ~/.pypirc)";
              command = ''
                 if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then echo "Run 'build' first."; exit 1; fi
                if [ ! -f "$HOME/.pypirc" ]; then echo "Warning: ~/.pypirc not found."; fi
                echo "--- Uploading to PyPI ---"
                twine upload dist/*
                echo "✅ Upload command executed."
              '';
            }
          ];
          devshell.startup.venvActivate.text = ''
             echo "Ensuring Python virtual environment is set up..."
            ${setupVenvScript}/bin/setup-venv
            echo "Activating virtual environment..."
            source .venv/bin/activate
            echo ""
            echo "✅ MCP-NixOS Dev Environment Activated."
            echo "   Virtual env ./.venv is active."
            echo ""
            menu
          '';
        };
      });
}
