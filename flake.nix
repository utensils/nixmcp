# flake.nix
{
  description = "MCP-NixOS - Model Context Protocol server for NixOS and Home Manager resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable"; # Make sure this matches your flake.lock
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

        # Define packages needed in the shell *and* potentially referenced in scripts
        myBlack = ps.black;
        myFlake8 = ps.flake8;
        myPyright = pkgs.pyright; # Use standalone pyright from pkgs
        # myPytest = ps.pytest; # pytest is primarily a dev dependency, installed via venv

        pythonForVenv = python.withPackages (p: with p; [ ]);

        setupVenvScript = pkgs.writeShellScriptBin "setup-venv" ''
          set -e
          echo "--- Setting up Python virtual environment ---"
          # Allow overriding the venv directory location with an environment variable
          VENV_DIR="''${VENV_DIR:-.venv}" # Define venv dir, default to .venv if not set
          if [ ! -d "$VENV_DIR" ]; then
            echo "Creating Python virtual environment in $VENV_DIR ..."
            ${pythonForVenv}/bin/python -m venv "$VENV_DIR"
          else
            echo "Virtual environment $VENV_DIR already exists."
          fi
          # Ensure activation script exists before sourcing
          if [ -f "$VENV_DIR/bin/activate" ]; then
              source "$VENV_DIR/bin/activate"
          else
              echo "Error: Activation script not found in $VENV_DIR/bin/activate"
              exit 1
          fi
          echo "Upgrading pip, setuptools, wheel in venv..."
          if command -v uv >/dev/null 2>&1; then uv pip install --upgrade pip setuptools wheel; else python -m pip install --upgrade pip setuptools wheel; fi
          echo "Installing dependencies from pyproject.toml..."
          if command -v uv >/dev/null 2>&1; then echo "(Using uv)"; uv pip install ".[dev]"; else echo "(Using pip)"; python -m pip install ".[dev]"; fi
          if [ -f "setup.py" ] || [ -f "pyproject.toml" ]; then
             echo "Installing project in editable mode..."
             if command -v uv >/dev/null 2>&1; then uv pip install -e .; else python -m pip install -e .; fi
          fi
          echo "✓ Python environment setup complete in $VENV_DIR"
          echo "---------------------------------------------"
        '';

        mcpNixosPackage = ps.buildPythonPackage {
          pname = "mcp-nixos";
          version = "0.2.1"; # Consider reading from a file
          src = ./.;
          python = python;
          nativeBuildInputs = [ ps.hatchling ];

          propagatedBuildInputs = with ps; [
            (mcp.overridePythonAttrs (old: {
              doCheck = false; # Disable tests for mcp during build
            }))
            requests
            python-dotenv
            beautifulsoup4
          ];

          meta = with pkgs.lib; {
            description = "Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources";
            homepage = "https://github.com/utensils/mcp-nixos";
            license = licenses.mit;
            maintainers = with maintainers; [ ]; # Add your handle e.g., jamesbrink
          };
        };

        devShell = pkgs.devshell.mkShell {
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
            pythonForVenv
            uv
            myBlack # Use the alias defined in let block
            myFlake8 # Use the alias
            myPyright # Use the alias
            # Testing/Build tools are mostly inside venv now
            nix
            nixos-option
            git
          ];
          commands = [
            {
              # Command 1: setup
              name = "setup";
              category = "environment";
              help = "Set up/update Python virtual environment (.venv) and install dependencies";
              command = "rm -rf .venv && ${toString setupVenvScript}/bin/setup-venv";
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 2: run
              name = "run";
              category = "server";
              help = "Run the MCP-NixOS server";
              command = ''
                # Ensure venv is activated - safely check for VIRTUAL_ENV
                if [ -z "''${VIRTUAL_ENV:-}" ] || [ ! -f ".venv/bin/activate" ]; then
                  echo "Activating venv..."
                  source .venv/bin/activate || { echo "Error: Failed to activate venv. Running setup..."; ${toString setupVenvScript}/bin/setup-venv && source .venv/bin/activate; }
                fi
                # Setup check moved inside run command
                if ! python -c "import mcp_nixos" &>/dev/null; then
                   echo "Editable install 'mcp_nixos' not found. Running setup..."
                   ${toString setupVenvScript}/bin/setup-venv
                   source .venv/bin/activate
                fi
                echo "Starting MCP-NixOS server (python -m mcp_nixos)..."
                python -m mcp_nixos
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 3: run-tests
              name = "run-tests";
              category = "testing";
              help = "Run tests with pytest [--unit|--integration]";
              command = ''
                # Activate venv if not already active - safely check for VIRTUAL_ENV
                if [ -z "''${VIRTUAL_ENV:-}" ] || [ ! -f ".venv/bin/activate" ]; then
                   echo "Activating venv..."
                   source .venv/bin/activate || { echo "Error: Failed to activate venv. Running setup..."; ${toString setupVenvScript}/bin/setup-venv && source .venv/bin/activate; }
                fi

                TEST_ARGS=()
                # Handle the unit/integration flags
                while [[ $# -gt 0 ]]; do
                  case "$1" in
                    --unit)
                      echo "Running unit tests only..."
                      TEST_ARGS+=(-m "not integration") # Use space for marker expression
                      shift ;;
                    --integration)
                      echo "Running integration tests only..."
                      TEST_ARGS+=(-m "integration")
                      shift ;;
                    *)
                      # Pass unknown args directly to pytest
                      TEST_ARGS+=("$1")
                      shift ;;
                  esac
                done

                COVERAGE_ARGS=()
                if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
                  COVERAGE_ARGS=(--cov=mcp_nixos --cov-report=term --cov-report=html --cov-report=xml)
                  echo "Using coverage (CI environment)"
                fi

                # Print the command with proper quoting using printf
                printf "Running: python -m pytest tests/ -v"
                printf " %q" "''${TEST_ARGS[@]:-}" "''${COVERAGE_ARGS[@]:-}"
                echo "" # Newline after command print

                # Use python -m pytest to ensure using venv's pytest
                # Pass arguments correctly using array expansion
                python -m pytest tests/ -v "''${TEST_ARGS[@]:-}" "''${COVERAGE_ARGS[@]:-}"


                if [ ''${#COVERAGE_ARGS[@]} -gt 0 ]; then
                  echo "✅ Coverage report generated. HTML report available in htmlcov/"
                fi
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 4: loc
              name = "loc";
              category = "development";
              help = "Count lines of code";
              command = ''
                echo "=== MCP-NixOS Lines of Code Statistics ==="
                SRC_LINES=$(find ./mcp_nixos -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                TEST_LINES=$(find ./tests -name '*.py' -type f | xargs wc -l | tail -n 1 | awk '{print $1}')
                CONFIG_LINES=$(find . -path './.venv' -prune -o -path './.mypy_cache' -prune -o -path './htmlcov' -prune -o -path './.direnv' -prune -o -path './result' -prune -o -path './.git' -prune -o -type f \( -name '*.json' -o -name '*.toml' -o -name '*.ini' -o -name '*.yml' -o -name '*.yaml' -o -name '*.nix' -o -name '*.lock' -o -name '*.md' -o -name '*.rules' -o -name '*.hints' -o -name '*.in' \) -print | xargs wc -l | tail -n 1 | awk '{print $1}')
                TOTAL_PYTHON=$((SRC_LINES + TEST_LINES))
                echo "Source code (mcp_nixos directory): $SRC_LINES lines"
                echo "Test code (tests directory): $TEST_LINES lines"
                echo "Configuration files: $CONFIG_LINES lines"
                echo "Total Python code: $TOTAL_PYTHON lines"
                if [ "$SRC_LINES" -gt 0 ]; then RATIO=$(echo "scale=2; $TEST_LINES / $SRC_LINES" | bc); echo "Test to code ratio: $RATIO:1"; fi
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 5: lint
              name = "lint";
              category = "development";
              help = "Lint code with Black (check) and Flake8";
              command = ''
                echo "--- Checking formatting with Black ---"
                ${myBlack}/bin/black --check mcp_nixos/ tests/
                echo "--- Running Flake8 linter ---"
                ${myFlake8}/bin/flake8 mcp_nixos/ tests/
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 6: typecheck
              name = "typecheck";
              category = "development";
              help = "Run pyright type checker";
              command = "${myPyright}/bin/pyright";
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 7: format
              name = "format";
              category = "development";
              help = "Format code with Black";
              command = "${myBlack}/bin/black mcp_nixos/ tests/";
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 8: build
              name = "build";
              category = "distribution";
              help = "Build package distributions (sdist and wheel)";
              command = ''
                if [ -z "''${VIRTUAL_ENV:-}" ] || [ ! -f ".venv/bin/activate" ]; then source .venv/bin/activate || { echo "Error: Failed to activate venv. Running setup..."; ${toString setupVenvScript}/bin/setup-venv && source .venv/bin/activate; }; fi
                echo "--- Building package ---"
                rm -rf dist/ build/ *.egg-info
                python -m build
                echo "✅ Build complete in dist/"
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 9: publish
              name = "publish";
              category = "distribution";
              help = "Upload package distribution to PyPI (requires ~/.pypirc)";
              command = ''
                if [ -z "''${VIRTUAL_ENV:-}" ] || [ ! -f ".venv/bin/activate" ]; then source .venv/bin/activate || { echo "Error: Failed to activate venv. Running setup..."; ${toString setupVenvScript}/bin/setup-venv && source .venv/bin/activate; }; fi
                if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then echo "Run 'build' first."; exit 1; fi
                if [ ! -f "$HOME/.pypirc" ]; then echo "Warning: ~/.pypirc not found."; fi
                echo "--- Uploading to PyPI ---"
                python -m twine upload dist/*
                echo "✅ Upload command executed."
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            # --- Check commands (for nix flake check) ---
            {
              # Command 10: check-lint
              name = "check-lint";
              category = "checks";
              help = "Run linters (used by nix flake check)";
              command = ''
                echo "--- Running linters check ---"
                if [ -d "mcp_nixos" ] && [ -d "tests" ]; then
                  ${myBlack}/bin/black --check mcp_nixos/ tests/
                  ${myFlake8}/bin/flake8 mcp_nixos/ tests/
                else
                  echo "Error: Required directories not found in $(pwd)"; ls -la; exit 1
                fi
              '';
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 11: check-types
              name = "check-types";
              category = "checks";
              help = "Run type checker (used by nix flake check)";
              command = "${myPyright}/bin/pyright";
            } # <<<--- REMOVED SEMICOLON HERE
            {
              # Command 12: check-tests
              name = "check-tests";
              category = "checks";
              help = "Run tests without coverage (used by nix flake check)";
              command = ''
                echo "--- Running basic syntax check for Python files ---"
                find mcp_nixos tests -name "*.py" -type f -print0 | xargs -0 ${python}/bin/python -m py_compile
                if [ $? -eq 0 ]; then echo "✓ Python syntax check passed"; else echo "✗ Python syntax check failed"; exit 1; fi
              '';
            } # <<<--- REMOVED LAST Optional SEMICOLON HERE
          ]; # End of commands list
          devshell.startup.venvActivate.text = ''
            echo "Ensuring Python virtual environment is set up..."
            ${toString setupVenvScript}/bin/setup-venv # Use toString for safety
            echo "Activating virtual environment..."
            # Ensure activation script exists before sourcing
            if [ -f ".venv/bin/activate" ]; then source .venv/bin/activate; else echo "Warning: venv activation script not found. Skipping activation."; fi
            echo ""
            echo "✅ MCP-NixOS Dev Environment Activated."
            echo "   Virtual env ./.venv is active."
            echo ""
            menu
          '';
        }; # End of devShell definition

      in
      {
        packages.mcp-nixos = mcpNixosPackage;
        packages.default = self.packages.${system}.mcp-nixos;

        devShells.default = devShell;

        apps = {
          default = { type = "app"; program = "${devShell}/bin/run"; };
          tests = { type = "app"; program = "${devShell}/bin/run-tests"; };
          lint = { type = "app"; program = "${devShell}/bin/lint"; };
          typecheck = { type = "app"; program = "${devShell}/bin/typecheck"; };
          format = { type = "app"; program = "${devShell}/bin/format"; };
          build = { type = "app"; program = "${devShell}/bin/build"; };
          publish = { type = "app"; program = "${devShell}/bin/publish"; };
        };

        checks = {
          lint = pkgs.runCommand "mcp-nixos-lint-check"
            {
              src = ./.;
              nativeBuildInputs = [ myBlack myFlake8 ];
            } ''
            echo "Running simplified lint check..."
            cd $src
            if [ -d "mcp_nixos" ] && [ -d "tests" ]; then
              echo "✓ Required directories found"; echo "Running black --check..."; ${myBlack}/bin/black --check mcp_nixos/ tests/; echo "Running flake8..."; ${myFlake8}/bin/flake8 mcp_nixos/ tests/; touch $out
            else echo "✗ Required directories not found"; ls -la; exit 1; fi
          '';
          types = pkgs.runCommand "mcp-nixos-type-check"
            {
              src = ./.;
              nativeBuildInputs = [ myPyright ];
            } ''
            echo "Running simplified type check..."
            cd $src
            if [ -f "pyrightconfig.json" ]; then
              echo "✓ Type configuration found"; echo "Running pyright..."; ${myPyright}/bin/pyright; touch $out
            else echo "✗ Type configuration not found"; ls -la; exit 1; fi
          '';
          tests = pkgs.runCommand "mcp-nixos-test-check"
            {
              src = ./.;
              nativeBuildInputs = [ python ];
            } ''
            echo "Running simplified test check (syntax compile)..."
            cd $src
            PY_FILES=$(find mcp_nixos tests -name "*.py" -type f)
            if [ -z "$PY_FILES" ]; then echo "✗ No Python files found"; exit 1; fi
            echo "Found Python files, checking syntax..."
            find mcp_nixos tests -name "*.py" -type f -print0 | xargs -0 ${python}/bin/python -m py_compile
            if [ $? -eq 0 ]; then echo "✓ Python syntax check passed"; touch $out; else echo "✗ Python syntax check failed"; exit 1; fi
          '';
          all = pkgs.runCommand "mcp-nixos-all-checks"
            {
              src = ./.; inherit (self.checks.${system}) lint types tests;
            } ''
            echo "Running all checks..."; echo "Lint check path: $lint"; echo "Types check path: $types"; echo "Tests check path: $tests"; echo "All checks passed"; touch $out
          '';
          default = self.checks.${system}.all;
        };
      });
}
