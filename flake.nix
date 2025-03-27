{
  description = "NixMCP - Model Context Protocol server for NixOS and Home Manager resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    devshell.url = "github:numtide/devshell";
  };

  outputs = { self, nixpkgs, flake-utils, devshell }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # Use the nixpkgs instance passed to the overlay
        pkgsForOverlay = import nixpkgs { inherit system; };

        # Import nixpkgs with overlays applied
        pkgs = import nixpkgs {
          inherit system;
          overlays = [
            devshell.overlays.default
          ];
        };

        # Configuration variables
        pythonVersion = "311";
        python = pkgs."python${pythonVersion}";
        ps = pkgs."python${pythonVersion}Packages"; # Python Packages shortcut

        # Base Python environment for creating the venv
        pythonForVenv = python.withPackages (p: with p; [ ]);

        # --- Optimized venv setup script ---
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

      in {
        # DevShell using numtide/devshell for enhanced features
        devShells.default = pkgs.devshell.mkShell {
          name = "nixmcp";

          # Basic MOTD shown before startup hooks
          motd = ''
            Entering NixMCP Dev Environment...
            Python: ${python.version}
            Nix:    ${pkgs.nix}/bin/nix --version
          '';

          # Environment variables
          env = [
            { name = "PYTHONPATH"; value = "$PWD"; }
            { name = "NIXMCP_ENV"; value = "development"; }
          ];

          # Packages available in the shell environment
          packages = with pkgs; [
            pythonForVenv
            nix
            nixos-option
            uv
            ps.black
            ps.flake8
            ps.pytest
            ps."pytest-cov"
            ps.build
            ps.twine
            git
          ];

          # Commands available via `menu`
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
              help = "Run the NixMCP server";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi
                if ! python -c "import nixmcp" &>/dev/null; then
                   echo "Editable install 'nixmcp' not found. Running setup..."
                   ${setupVenvScript}/bin/setup-venv
                   source .venv/bin/activate
                fi
                echo "Starting NixMCP server (python -m nixmcp)..."
                python -m nixmcp
              '';
            }
            # --- RESTORED run-tests COMMAND ---
            {
              name = "run-tests"; # Changed name back from 'test'
              category = "testing";
              help = "Run tests with pytest [--no-coverage]";
              command = ''
                # Ensure venv is active
                if [ -z "$VIRTUAL_ENV" ]; then
                  echo "Activating venv..."
                  source .venv/bin/activate
                fi

                # Tools (pytest, pytest-cov) are provided by Nix

                # Parse arguments for coverage
                COVERAGE_ARGS="--cov=nixmcp --cov-report=term-missing --cov-report=html"
                PYTEST_ARGS=""
                for arg in "$@"; do
                  case $arg in
                    --no-coverage)
                      COVERAGE_ARGS=""
                      echo "Running without coverage reporting..."
                      shift
                      ;;
                    *)
                      PYTEST_ARGS="$PYTEST_ARGS $arg"
                      shift
                      ;;
                  esac
                done

                # Determine source directory for coverage
                SOURCE_DIR="nixmcp" # Adjust as needed
                if [ ! -d "$SOURCE_DIR" ]; then
                   if [ -d "server" ]; then
                       SOURCE_DIR="server"
                   else
                       # If neither specific dir exists, maybe just target tests/ ?
                       # Or adjust coverage args if appropriate. For now, keep potential '.' fallback
                       echo "Warning: Source directory '$SOURCE_DIR' or 'server' not found."
                       SOURCE_DIR="." # Fallback, may need adjustment for specific project
                   fi
                   # Update coverage args if source dir changed
                   if [ "$SOURCE_DIR" != "nixmcp" ]; then
                      COVERAGE_ARGS=$(echo "$COVERAGE_ARGS" | sed "s/--cov=nixmcp/--cov=$SOURCE_DIR/")
                   fi
                fi

                echo "Running tests..."
                pytest tests/ -v $COVERAGE_ARGS $PYTEST_ARGS

                if [ -n "$COVERAGE_ARGS" ] && echo "$COVERAGE_ARGS" | grep -q 'html'; then
                  echo "✅ Coverage report generated. HTML report available in htmlcov/"
                elif [ -n "$COVERAGE_ARGS" ]; then
                   echo "✅ Coverage report generated."
                fi
              '';
            }
            {
              name = "lint";
              category = "development";
              help = "Lint code with Black (check) and Flake8";
              command = ''
                echo "--- Checking formatting with Black ---"
                if [ -d "nixmcp" ]; then black --check nixmcp/ tests/
                elif [ -d "server" ]; then black --check server/ tests/ *.py
                else black --check --exclude='\.venv/' *.py tests/; fi
                echo "--- Running Flake8 linter ---"
                if [ -d "nixmcp" ]; then flake8 nixmcp/ tests/
                elif [ -d "server" ]; then flake8 server/ tests/ *.py
                else flake8 --exclude='\.venv/' *.py tests/; fi
              '';
            }
            {
              name = "format";
              category = "development";
              help = "Format code with Black";
              command = ''
                echo "--- Formatting code with Black ---"
                if [ -d "nixmcp" ]; then black nixmcp/ tests/
                elif [ -d "server" ]; then black server/ tests/ *.py
                else black --exclude='\.venv/' *.py tests/; fi
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

          # --- STARTUP HOOK WITH AUTO MENU ---
          devshell.startup.venvActivate.text = ''
            # Run the setup script non-interactively first to ensure venv exists
            echo "Ensuring Python virtual environment is set up..."
            ${setupVenvScript}/bin/setup-venv

            # Activate the virtual environment for the interactive shell
            echo "Activating virtual environment..."
            source .venv/bin/activate

            echo ""
            echo "✅ NixMCP Dev Environment Activated."
            echo "   Virtual env ./.venv is active."
            echo ""

            # Automatically display the devshell menu
            menu
          '';
        };

      });
}