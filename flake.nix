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

        # Use a single Python instance with proper library support
        pythonWithLibs = python.buildEnv.override {
          extraLibs = [
            ps.cffi
            ps.wheel
            ps.setuptools
            ps.pip
          ];
          ignoreCollisions = true;
        };

        setupVenvScript = pkgs.writeShellScriptBin "setup-venv" ''
          set -e
          echo "--- Setting up Python virtual environment ---"

          # Check for pyproject.toml or setup.py
          if [ ! -f "pyproject.toml" ] && [ ! -f "setup.py" ]; then
            echo "Error: Neither pyproject.toml nor setup.py found. Cannot install dependencies."
            exit 1
          fi

          if [ ! -d ".venv" ]; then
            echo "Creating Python virtual environment in ./.venv ..."
            ${pythonWithLibs}/bin/python -m venv .venv
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

          echo "Installing dependencies from pyproject.toml..."
          if command -v uv >/dev/null 2>&1; then
            echo "(Using uv)"
            # Install with all optional dependencies for development
            uv pip install ".[dev]"
          else
            echo "(Using pip)"
            python -m pip install ".[dev]"
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

          # List installed packages for verification
          echo "Installed dependencies:"
          pip list | grep -E "requests|mcp|beautifulsoup4|python-dotenv"
          
          echo "✓ Python environment setup complete in ./.venv"
          echo "---------------------------------------------"
        '';

      in
      {
        # Create a separate shell for website development
        devShells.web = pkgs.devshell.mkShell {
          name = "mcp-nixos-web";
          packages = with pkgs; [
            nodejs_20
            awscli2
          ];
          commands = [
            {
              name = "install";
              category = "website";
              help = "Install website dependencies";
              command = "cd website && npm install";
            }
            {
              name = "dev";
              category = "website";
              help = "Start the development server";
              command = "cd website && npm run dev";
            }
            {
              name = "build";
              category = "website";
              help = "Build the static website for production";
              command = "cd website && npm run build";
            }
            {
              name = "lint";
              category = "website";
              help = "Lint the website code";
              command = "cd website && npm run lint";
            }
            {
              name = "deploy";
              category = "website";
              help = "Deploy website to AWS S3 and invalidate CloudFront cache. Usage: deploy [profile-name]";
              command = ''
                echo "--- Building and deploying website to AWS S3 ---"
                
                # Set AWS profile flag if provided
                PROFILE_FLAG=""
                if [ $# -gt 0 ]; then
                  PROFILE_FLAG="--profile $1"
                  echo "Using AWS profile: $1"
                else
                  # Safely check if environment variables are set
                  if ! env | grep -q "^AWS_ACCESS_KEY_ID=" || ! env | grep -q "^AWS_SECRET_ACCESS_KEY="; then
                    echo "⚠️ Note: No AWS credentials in environment variables"
                    echo ""
                    echo "You can authenticate using one of these methods:"
                    echo ""
                    echo "1. AWS Profile (recommended):"
                    echo "   deploy profile-name    # Example: deploy personal"
                    echo ""
                    echo "2. Environment Variables:"
                    echo "   export AWS_ACCESS_KEY_ID=AKIAXXXXXXXX"
                    echo "   export AWS_SECRET_ACCESS_KEY=XXXXXXXX"
                    echo "   deploy"
                    echo ""
                    echo "3. Default AWS Config:"
                    echo "   If you have default credentials in ~/.aws/config or ~/.aws/credentials"
                    echo "   those will be used automatically"
                    echo ""
                    # Exit with error code
                    echo "❌ No valid AWS credentials found. Please configure authentication and try again."
                    exit 1
                  fi
                fi
                
                # Build the website
                echo "Building website..."
                cd website && npm run build
                
                # Return to the original directory
                cd ..
                
                # Deploy to S3
                echo "Deploying to S3 bucket urandom-mcp-nixos..."
                
                # Check if the out directory exists
                if [ ! -d "website/out" ]; then
                  echo "❌ Error: Output directory 'website/out' does not exist."
                  echo "    This may indicate the build failed or ran in a different location."
                  exit 1
                fi
                
                # Deploy to S3
                echo "Syncing files to S3..."
                aws s3 sync website/out/ s3://urandom-mcp-nixos/ --delete $PROFILE_FLAG
                
                # Check if the previous command succeeded
                if [ $? -ne 0 ]; then
                  echo "❌ Error: S3 sync failed"
                  exit 1
                fi
                
                # Invalidate CloudFront cache
                echo "Invalidating CloudFront cache..."
                DISTRIBUTION_ID="E1QS1G7FYYJ6TL"
                aws cloudfront create-invalidation --distribution-id $DISTRIBUTION_ID --paths "/*" $PROFILE_FLAG
                
                echo "✅ Website deployment complete"
              '';
            }
          ];
          devshell.startup.initMessage.text = ''
            echo "Entering MCP-NixOS Website Dev Environment..."
            echo ""
            echo "Available commands:"
            echo "  install  - Install dependencies"
            echo "  dev      - Start development server"
            echo "  build    - Build for production"
            echo "  lint     - Lint code"
            echo "  deploy   - Deploy website to AWS S3/CloudFront"
            echo ""
            menu
          '';
        };
        
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
            { name = "LIBFFI_INCLUDE_DIR"; value = "${pkgs.libffi.dev}/include"; } # Add .dev
            # Make sure Python can find _ctypes with correct linking flags
            { name = "NIX_LDFLAGS"; value = "-L${pkgs.libffi}/lib -L${pkgs.libffi.out}/lib"; }
            { name = "NIX_CFLAGS_COMPILE"; value = "-I${pkgs.libffi.dev}/include"; }
            # For macOS specifically
            { name = "DYLD_LIBRARY_PATH"; value = "${pkgs.libffi}/lib:${pkgs.libffi.out}/lib"; }
            # Add SDK path for macOS if needed
            { name = "SDKROOT"; value = "${pkgs.darwin.apple_sdk.frameworks.CoreServices}"; }
          ];
          packages = with pkgs; [
            # Python with build dependencies
            pythonWithLibs
            uv # Faster pip alternative
            ps.build
            ps.twine
            # Required for building C extensions
            libffi
            pkg-config
            # Build tools needed for extension compilation
            binutils
            stdenv.cc.cc

            # Linters & Formatters
            ps.black
            ps.flake8
            # Standalone pyright package for cross-platform type checking
            pyright

            # Testing
            ps.pytest
            ps."pytest-cov"
            # ps.pytest-asyncio # Usually installed via pip/uv into venv

            # Nix & Git
            nix
            nixos-option
            git

            # AI Tools
            code2prompt
            llm

            # Remove Node.js from main dev shell to avoid conflicts
          ];
          commands = [
            {
              name = "setup";
              category = "environment";
              help = "Set up/update Python virtual environment (.venv) and install dependencies";
              command = "rm -rf .venv && ${setupVenvScript}/bin/setup-venv";
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
                echo "Starting MCP-NixOS server with enhanced termination handling..."
                # Use the wrapper script for improved signal handling
                python -m mcp_nixos.run
              '';
            }
            {
              name = "run-tests";
              category = "testing";
              help = "Run tests with pytest [--unit|--integration]";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then
                  echo "Activating venv..."
                  source .venv/bin/activate
                fi
                
                # Verify key dependencies
                echo "Verifying dependencies before running tests..."
                if ! python -c "import requests" &>/dev/null; then
                  echo "ERROR: 'requests' package not found. Installing explicitly..."
                  if command -v uv >/dev/null 2>&1; then
                    uv pip install requests>=2.32.3
                  else
                    python -m pip install requests>=2.32.3
                  fi
                fi
                
                # Set up parameters based on arguments
                TEST_ARGS=""
                
                # Handle the unit/integration flags
                # These arguments get passed directly to pytest
                if [[ $# -gt 0 && "$1" == "--unit" ]]; then
                  echo "Running unit tests only..."
                  TEST_ARGS="--unit"
                  shift
                elif [[ $# -gt 0 && "$1" == "--integration" ]]; then
                  echo "Running integration tests only..."
                  TEST_ARGS="--integration"
                  shift
                else
                  echo "Running all tests..."
                  # Set environment variable to indicate all tests are running
                  # This helps certain tests that need to run in isolation skip when run in a full suite
                  export RUNNING_ALL_TESTS=1
                fi
                
                # Check if running in CI environment
                COVERAGE_ARGS=""
                JUNIT_ARGS=""
                if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
                  # In CI, use coverage and generate JUnit XML for Codecov Test Analytics
                  COVERAGE_ARGS="--cov=mcp_nixos --cov-report=term --cov-report=html --cov-report=xml"
                  JUNIT_ARGS="--junitxml=junit.xml -o junit_family=legacy"
                  echo "Using coverage and JUnit XML (CI environment)"
                fi
                
                # Simple and direct test execution
                if [ -n "$TEST_ARGS" ]; then
                  echo "Running: pytest tests/ -v $TEST_ARGS $COVERAGE_ARGS $JUNIT_ARGS $@"
                  eval "pytest tests/ -v $TEST_ARGS $COVERAGE_ARGS $JUNIT_ARGS $@"
                else
                  echo "Running: pytest tests/ -v $COVERAGE_ARGS $JUNIT_ARGS $@"
                  pytest tests/ -v $COVERAGE_ARGS $JUNIT_ARGS "$@"
                fi
                
                # Show coverage report message if applicable
                if [ -n "$COVERAGE_ARGS" ]; then
                  echo "✅ Coverage report generated. HTML report available in htmlcov/"
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
              help = "Format with Black and then lint code with Flake8 (only checks format in CI)";
              command = ''
                # Check if running in CI environment
                if [ "$(printenv CI 2>/dev/null)" != "" ] || [ "$(printenv GITHUB_ACTIONS 2>/dev/null)" != "" ]; then
                  echo "--- CI detected: Checking formatting with Black ---"
                  black --check mcp_nixos/ tests/
                else
                  echo "--- Formatting code with Black ---"
                  black mcp_nixos/ tests/
                fi
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
            {
              name = "sync-rules";
              category = "development";
              help = "Sync CLAUDE.md to .windsurfrules, .cursorrules, and .goosehints files";
              command = ''
                echo "--- Syncing CLAUDE.md to rule files ---"
                if [ ! -f "CLAUDE.md" ]; then
                  echo "❌ Error: CLAUDE.md file not found!"
                  exit 1
                fi
                
                # Copy content to rule files
                cat CLAUDE.md > .windsurfrules
                cat CLAUDE.md > .cursorrules
                cat CLAUDE.md > .goosehints
                
                # Verify sync
                echo "✅ CLAUDE.md synced to:"
                echo "   - .windsurfrules"
                echo "   - .cursorrules"
                echo "   - .goosehints"
              '';
            }
            {
              name = "web-dev";
              category = "website";
              help = "Launch Node.js shell for website development";
              command = ''
                echo "--- Launching Node.js shell for website development ---"
                nix develop .#web
              '';
            }
            {
              name = "complexity";
              category = "development";
              help = "Run wily to analyze code complexity (requires command argument: build|report|graph|rank|diff)";
              command = ''
                if [ -z "$VIRTUAL_ENV" ]; then source .venv/bin/activate; fi
                
                # Check if wily is installed
                if ! command -v wily >/dev/null 2>&1; then
                  echo "Installing wily..."
                  if command -v uv >/dev/null 2>&1; then
                    uv pip install wily
                  else
                    python -m pip install wily
                  fi
                fi
                
                # Check if argument is provided
                if [ $# -eq 0 ]; then
                  echo "=== Wily Code Complexity Analysis ==="
                  echo "Error: Missing required command argument"
                  echo ""
                  echo "Usage: complexity <command> [args]"
                  echo ""
                  echo "Commands:"
                  echo "  build         - Build the wily cache (run this first)"
                  echo "  report <file> <metric> - Show metrics for a file"
                  echo "  graph <file> <metric>  - Generate graph visualization"
                  echo "  rank [path] [metric]   - Rank files by complexity"
                  echo "  diff [git_ref]         - Show complexity changes (default: HEAD^1)"
                  echo "  list-metrics  - List available metrics"
                  echo ""
                  echo "Examples:"
                  echo "  complexity build"
                  echo "  complexity report mcp_nixos/server.py mi"
                  echo "  complexity diff origin/main"
                  exit 1
                fi
                
                # Subcommands
                case "$1" in
                  build)
                    echo "--- Building wily cache ---"
                    wily build mcp_nixos tests
                    ;;
                  report)
                    echo "--- Generating wily report ---"
                    if [ -z "$2" ]; then
                      echo "Usage: complexity report <file_path> <metric>"
                      echo "Available metrics: mi (maintainability index), raw.loc (lines of code), etc."
                      echo "Run 'wily list-metrics' for a complete list"
                      exit 1
                    fi
                    if [ -z "$3" ]; then
                      wily report "$2" "mi"
                    else
                      wily report "$2" "$3"
                    fi
                    ;;
                  graph)
                    echo "--- Generating wily graph ---"
                    if [ -z "$2" ]; then
                      echo "Usage: complexity graph <file_path> <metric>"
                      echo "Available metrics: mi (maintainability index), raw.loc (lines of code), etc."
                      echo "Run 'wily list-metrics' for a complete list"
                      exit 1
                    fi
                    if [ -z "$3" ]; then
                      wily graph "$2" "mi"
                    else
                      wily graph "$2" "$3"
                    fi
                    ;;
                  rank)
                    echo "--- Ranking files by complexity ---"
                    if [ -z "$2" ]; then
                      PATH_ARG="."
                    else
                      PATH_ARG="$2"
                    fi
                    
                    if [ -z "$3" ]; then
                      wily rank "$PATH_ARG" "mi"
                    else
                      wily rank "$PATH_ARG" "$3"
                    fi
                    ;;
                  diff)
                    echo "--- Comparing complexity changes ---"
                    if [ -z "$2" ]; then
                      wily diff mcp_nixos tests -r "HEAD^1"
                    else
                      wily diff mcp_nixos tests -r "$2"
                    fi
                    ;;
                  list-metrics)
                    wily list-metrics
                    ;;
                  *)
                    echo "=== Wily Code Complexity Analysis ==="
                    echo "Error: Missing required command argument"
                    echo ""
                    echo "Usage: complexity <command> [args]"
                    echo ""
                    echo "Commands:"
                    echo "  build         - Build the wily cache (run this first)"
                    echo "  report <file> <metric> - Show metrics for a file"
                    echo "  graph <file> <metric>  - Generate graph visualization"
                    echo "  rank [path] [metric]   - Rank files by complexity"
                    echo "  diff [git_ref]         - Show complexity changes (default: HEAD^1)"
                    echo "  list-metrics  - List available metrics"
                    echo ""
                    echo "Examples:"
                    echo "  complexity build"
                    echo "  complexity report mcp_nixos/server.py mi"
                    echo "  complexity diff origin/main"
                    exit 1
                    ;;
                esac
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
