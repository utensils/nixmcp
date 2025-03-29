# flake.nix
{
  description = "MCP-NixOS - Model Context Protocol server for NixOS, Home Manager, and nix-darwin resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        # --- Package Set ---
        pkgs = import nixpkgs { inherit system; };

        # --- Python Setup ---
        pythonVersion = "311";
        python = pkgs."python${pythonVersion}";
        ps = pkgs."python${pythonVersion}Packages";

        # --- Dependencies ---
        runtimeDeps = with ps; [
          (mcp.overridePythonAttrs (old: { }))
          requests
          python-dotenv
          beautifulsoup4
        ];
        nativeDevDeps = with pkgs; [ black pyright git nix nixos-option uv bc ];
        # --- FIX: Removed pyright from pythonDevDeps ---
        pythonDevDeps = with ps; [ flake8 pytest pytest-cov pytest-asyncio ];
        # ---------------------------------------------
        buildDeps = with ps; [ hatchling ];

        # --- Project Package ---
        mcpNixosPackage = ps.buildPythonPackage {
          pname = "mcp-nixos";
          version = "0.2.1";
          src = ./.;
          nativeBuildInputs = buildDeps;
          propagatedBuildInputs = runtimeDeps;
          checkInputs = pythonDevDeps;
          doCheck = false; # Rely on checks.tests
          pythonImportsCheck = [ "mcp_nixos" ];
          meta = with pkgs.lib; {
            description = "MCP server for NixOS/Home Manager/nix-darwin resources";
            homepage = "https://github.com/utensils/mcp-nixos";
            license = licenses.mit;
            maintainers = [ ];
          };
        };

        # --- Venv Setup Script ---
        venvPython = python.withPackages (p: [ ]);
        setupVenvScript = pkgs.writeShellScriptBin "setup-venv" ''
          set -e
          echo "--- Setting up Python virtual environment ---"
          VENV_DIR="''${VENV_DIR:-.venv}"
          echo "Using VENV_DIR: $VENV_DIR"
          mkdir -p "$(dirname "$VENV_DIR")"
          echo "Removing old venv if it exists..."
          rm -rf "$VENV_DIR"
          echo "Creating Python virtual environment in $VENV_DIR..."
          ${venvPython}/bin/python -m venv "$VENV_DIR"
          echo "Activating venv for setup..."
          source "$VENV_DIR/bin/activate"
          echo "Upgrading pip tools..."
          if command -v uv >/dev/null 2>&1; then
            uv pip install --upgrade pip setuptools wheel
          else
            python -m pip install --upgrade pip setuptools wheel
          fi
          echo "Installing dependencies from pyproject.toml..."
          if command -v uv >/dev/null 2>&1; then
            uv pip install ".[dev]"
          else
            python -m pip install ".[dev]" -e .
          fi
          echo "Deactivating venv after setup."
          deactivate
          echo "✓ Python environment setup complete in $VENV_DIR"
          echo "---------------------------------------------"
        '';

        # --- Development Shell ---
        devShell = pkgs.mkShell {
          name = "mcp-nixos-shell";
          packages = [ venvPython ] ++ nativeDevDeps ++ (with ps; [ flake8 ]);
          shellHook = ''
            echo "--- MCP-NixOS Development Shell ---"
            if [ ! -f ".venv/bin/activate" ]; then
              echo "Virtual environment (.venv) not found."
              echo "Run 'nix run .#setup' to create it."
            else
              echo "Activate venv with: source .venv/bin/activate (or use direnv)"
            fi
            echo "Available commands: setup, run, test, lint, typecheck, format, build, publish, loc"
            echo "------------------------------------"
          '';
        };

        # --- Check Environment ---
        # Python env with runtime + test deps needed by pyright/pytest
        checkEnv = python.withPackages (ps: runtimeDeps ++ pythonDevDeps);

        # --- Scripts for Apps/Commands ---
        scripts = {
          setup = setupVenvScript;
          run = pkgs.writeShellScriptBin "run-mcp-nixos" ''
            set -e
            if [ ! -f ".venv/bin/activate" ]; then echo "Venv not found, running setup first..."; "${setupVenvScript}/bin/setup-venv"; fi
            source .venv/bin/activate
            
            # Make sure cache directory exists and is properly set
            if [ -z "$MCP_NIXOS_CACHE_DIR" ]; then
              export MCP_NIXOS_CACHE_DIR=~/.cache/mcp_nixos
              mkdir -p "$MCP_NIXOS_CACHE_DIR"
              echo "Using default cache directory: $MCP_NIXOS_CACHE_DIR"
            else
              echo "Using existing cache directory: $MCP_NIXOS_CACHE_DIR"
            fi
            
            echo "Starting MCP-NixOS server..."
            python -m mcp_nixos "$@"
          '';
          test = pkgs.writeShellScriptBin "test-mcp-nixos" ''
            set -e
            if [ ! -f ".venv/bin/activate" ]; then echo "Venv not found, running setup first..."; "${setupVenvScript}/bin/setup-venv"; fi
            source .venv/bin/activate
            TEST_ARGS=()
            MARKER_ARGS=""
            PYTEST_EXTRA_ARGS=()
            while [[ $# -gt 0 ]]; do
              case "$1" in
                --unit) MARKER_ARGS="-m 'not integration'"; shift ;;
                --integration) MARKER_ARGS="-m integration"; shift ;;
                *) PYTEST_EXTRA_ARGS+=("$1"); shift ;;
              esac
            done
            if [ -n "$MARKER_ARGS" ]; then TEST_ARGS+=("$MARKER_ARGS"); fi
            TEST_ARGS+=("''${PYTEST_EXTRA_ARGS[@]:-}")
            COVERAGE_ARGS=()
            if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
              COVERAGE_ARGS=(--cov=mcp_nixos --cov-report=term --cov-report=html --cov-report=xml)
              echo "Running with coverage (CI environment detected)"
            fi
            
            # Set a consistent test cache directory
            if [ -z "$MCP_NIXOS_CACHE_DIR" ]; then
              export MCP_NIXOS_CACHE_DIR=$(mktemp -d)/mcp_nixos_cache
              mkdir -p "$MCP_NIXOS_CACHE_DIR"
              echo "Using test cache directory: $MCP_NIXOS_CACHE_DIR"
            else
              echo "Using existing cache directory: $MCP_NIXOS_CACHE_DIR"
            fi
            
            echo "Running pytest..."
            set -x
            python -m pytest tests/ -v "''${TEST_ARGS[@]:-}" "''${COVERAGE_ARGS[@]:-}"
            set +x
            if [ ''${#COVERAGE_ARGS[@]} -gt 0 ]; then
              echo "✅ Coverage report generated. HTML report available in htmlcov/"
            fi
          '';
          lint = pkgs.writeShellScriptBin "lint-mcp-nixos" ''
            set -e
            echo "--- Running Linters ---"
            echo "Running black --check..."
            ${pkgs.black}/bin/black --check mcp_nixos/ tests/
            echo "Running flake8..."
            ${ps.flake8}/bin/flake8 mcp_nixos/ tests/
          '';
          typecheck = pkgs.writeShellScriptBin "typecheck-mcp-nixos" ''
            set -e
            echo "--- Running Type Checker ---"
            ${pkgs.pyright}/bin/pyright
          '';
          format = pkgs.writeShellScriptBin "format-mcp-nixos" ''
            set -e
            echo "--- Formatting Code ---"
            ${pkgs.black}/bin/black mcp_nixos/ tests/
          '';
          build = pkgs.writeShellScriptBin "build-mcp-nixos" ''
            set -e
            if [ ! -f ".venv/bin/activate" ]; then echo "Venv not found, running setup first..."; "${setupVenvScript}/bin/setup-venv"; fi
            source .venv/bin/activate
            echo "--- Building package ---"
            rm -rf dist/ build/ *.egg-info
            python -m build
            echo "✅ Build complete in dist/"
            ls -l dist/
          '';
          publish = pkgs.writeShellScriptBin "publish-mcp-nixos" ''
            set -e
            if [ ! -f ".venv/bin/activate" ]; then echo "Venv not found, running setup first..."; "${setupVenvScript}/bin/setup-venv"; fi
            source .venv/bin/activate
            if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then echo "Run 'build' first."; exit 1; fi
            echo "--- Uploading to PyPI ---"
            python -m twine upload dist/*
            echo "✅ Upload command executed."
          '';
          loc = pkgs.writeShellScriptBin "loc-mcp-nixos" ''
            echo "=== MCP-NixOS Lines of Code Statistics ==="
            SRC_LINES=$(find ./mcp_nixos -name '*.py' -type f -print0 | xargs -0 wc -l | tail -n 1 | awk '{print $1}')
            TEST_LINES=$(find ./tests -name '*.py' -type f -print0 | xargs -0 wc -l | tail -n 1 | awk '{print $1}')
            CONFIG_LINES=$(find . -path './.venv' -prune -o -path './.mypy_cache' -prune -o -path './htmlcov' -prune -o -path './.direnv' -prune -o -path './result' -prune -o -path './.git' -prune -o -type f \( -name '*.json' -o -name '*.toml' -o -name '*.ini' -o -name '*.yml' -o -name '*.yaml' -o -name '*.nix' -o -name '*.lock' -o -name '*.md' -o -name '*.rules' -o -name '*.hints' -o -name '*.in' \) -print0 | xargs -0 wc -l | tail -n 1 | awk '{print $1}')
            TOTAL_PYTHON=$((SRC_LINES + TEST_LINES))
            echo "Source code (mcp_nixos directory): $SRC_LINES lines"
            echo "Test code (tests directory): $TEST_LINES lines"
            echo "Configuration files: $CONFIG_LINES lines"
            echo "Total Python code: $TOTAL_PYTHON lines"
            if [ "$SRC_LINES" -gt 0 ]; then RATIO=$(echo "scale=2; $TEST_LINES / $SRC_LINES" | bc); echo "Test to code ratio: $RATIO:1"; fi
          '';
        }; # End of scripts

        # --- Checks for `nix flake check` ---
        checks = {
          lint = pkgs.runCommand "mcp-nixos-check-lint-${system}"
            {
              src = ./.;
              nativeBuildInputs = [ pkgs.black ps.flake8 ];
              strictDeps = true;
            } ''
            echo "Running lint check..."
            cd $src
            ${pkgs.black}/bin/black --check mcp_nixos/ tests/
            ${ps.flake8}/bin/flake8 mcp_nixos/ tests/
            touch $out
          '';
          types = pkgs.runCommand "mcp-nixos-check-types-${system}"
            {
              src = ./.;
              # Provide python env + pyright executable
              nativeBuildInputs = [ checkEnv pkgs.pyright ];
              strictDeps = true;
            } ''
            echo "Running type check..."
            cd $src
            export PYTHONPATH=$PWD:$PYTHONPATH
            ${pkgs.pyright}/bin/pyright
            touch $out
          '';
          tests = pkgs.runCommand "mcp-nixos-check-tests-${system}"
            {
              src = ./.;
              nativeBuildInputs = [ checkEnv ];
              strictDeps = true;
            } ''
            echo "Running tests with pytest..."
            cd $src
            export PYTHONPATH=$PWD:$PYTHONPATH
            echo "PYTHONPATH=$PYTHONPATH"
            # Set up a proper home directory for the tests
            export HOME=$TMPDIR/homeless-shelter
            mkdir -p $HOME/Library/Caches
            
            # Set cache directory to match what tests expect
            export MCP_NIXOS_CACHE_DIR=$HOME/Library/Caches/mcp_nixos
            mkdir -p $MCP_NIXOS_CACHE_DIR
            echo "Using test cache directory: $MCP_NIXOS_CACHE_DIR"
            
            # Make the temporary directories writable
            chmod -R 755 $HOME
            
            # Run tests without the cache provider flag to allow proper caching
            ${checkEnv}/bin/python -m pytest tests/ -m "not integration" -v
            touch $out
          '';
          all = pkgs.runCommand "mcp-nixos-check-all-${system}"
            {
              buildInputs = [
                self.checks.${system}.lint
                self.checks.${system}.types
                self.checks.${system}.tests
              ];
              strictDeps = true;
            } ''
            echo "All checks passed!"
            touch $out
          '';
          default = self.checks.${system}.all;
        }; # End of checks

      in
      {
        packages = {
          mcp-nixos = mcpNixosPackage;
          default = mcpNixosPackage;
        };
        devShells.default = devShell;
        apps = {
          default = flake-utils.lib.mkApp { drv = scripts.run; };
          setup = flake-utils.lib.mkApp { drv = scripts.setup; };
          tests = flake-utils.lib.mkApp { drv = scripts.test; };
          lint = flake-utils.lib.mkApp { drv = scripts.lint; };
          typecheck = flake-utils.lib.mkApp { drv = scripts.typecheck; };
          format = flake-utils.lib.mkApp { drv = scripts.format; };
          build = flake-utils.lib.mkApp { drv = scripts.build; };
          publish = flake-utils.lib.mkApp { drv = scripts.publish; };
          loc = flake-utils.lib.mkApp { drv = scripts.loc; };
        };
        checks = checks;
      }
    ); # End of eachDefaultSystem
}
