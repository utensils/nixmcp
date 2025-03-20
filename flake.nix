{
  description = "NixMCP - Model Context Protocol server for NixOS resources";

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
        
        # Create a Python environment with all our dependencies
        python = pkgs.python311;
        pythonEnv = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          # Note: venv is built into Python, not a separate package
        ]);

        # Create a wrapper script to initialize venv and install packages
        setupScript = pkgs.writeShellScriptBin "setup-env" ''
          #!/usr/bin/env bash
          
          # Check if .venv exists and create it if needed
          if [ ! -d .venv ]; then
            echo "Creating Python virtual environment..."
            ${pythonEnv}/bin/python -m venv .venv
            source .venv/bin/activate
            pip install "mcp>=1.4.0" fastapi uvicorn requests
          else
            source .venv/bin/activate
          fi
          
          # Print environment info
          echo ""
          echo "Welcome to NixMCP development environment!"
          echo "Python version: $(python --version)"
          echo "Nix version: $(nix --version)"
          echo ""
          echo "MCP SDK is installed in .venv/"
          echo "Run the server with: python server.py"
          echo "Access the MCP Inspector at: http://localhost:8000/docs"
        '';

      in {
        # DevShell implementations
        devShells = {
          # Use devshell as default for better developer experience
          default = pkgs.devshell.mkShell {
            name = "nixmcp";
            
            # Better prompt appearance
            motd = ''
              NixMCP Dev Environment - Model Context Protocol for NixOS resources
            '';
            
            # Environment variables
            env = [
              { name = "PYTHONPATH"; value = "."; }
              { name = "NIXMCP_ENV"; value = "development"; }
              { name = "PS1"; value = "\\[\\e[1;36m\\][nixmcp]\\[\\e[0m\\]$ "; }
            ];
            
            packages = with pkgs; [
              # Python environment
              pythonEnv
              
              # Required Nix tools
              nix
              nixos-option
              
              # Development tools
              black
              mypy
              python311Packages.pytest
            ];
            
            # Startup commands
            commands = [
              {
                name = "setup";
                category = "development";
                help = "Set up Python environment and install dependencies";
                command = ''
                  echo "Setting up Python virtual environment..."
                  ${pythonEnv}/bin/python -m venv .venv
                  source .venv/bin/activate
                  pip install -r requirements.txt
                  echo "✓ Setup complete!"
                '';
              }
              {
                name = "setup-test";
                category = "development";
                help = "Set up Python environment for testing with type stubs";
                command = ''
                  echo "Setting up Python testing environment..."
                  source .venv/bin/activate
                  pip install pytest types-requests
                  echo "✓ Test setup complete!"
                '';
              }
              {
                name = "run";
                category = "server";
                help = "Run the NixMCP server";
                command = ''
                  echo "Starting NixMCP server..."
                  source .venv/bin/activate
                  python server.py
                '';
              }
              {
                name = "test";
                category = "testing";
                help = "Run tests (automatically manages server)";
                command = ''
                  echo "Running tests with automatic server management..."
                  source .venv/bin/activate
                  
                  # Check if pytest is installed
                  if ! python -c "import pytest" 2>/dev/null; then
                    echo "⚠️  pytest not found, installing..."
                    pip install pytest types-requests
                  fi
                  
                  # Run the test script directly with unbuffered output
                  echo "Starting tests..."
                  python -u test_mcp.py
                  TEST_EXIT=$?
                  
                  # Report test result
                  if [ $TEST_EXIT -ne 0 ]; then
                    echo -e "\n❌ Tests failed with exit code $TEST_EXIT"
                    exit $TEST_EXIT
                  else
                    echo -e "\n✅ All tests passed!"
                  fi
                '';
              }
              {
                name = "test-dry";
                category = "testing";
                help = "Run test mocks (no server needed)";
                command = ''
                  echo "Running test dry run..."
                  source .venv/bin/activate
                  
                  # Run dry test with unbuffered output
                  echo "Starting dry run tests..."
                  python -u test_mcp.py --dry-run
                  TEST_EXIT=$?
                  
                  # Report test result
                  if [ $TEST_EXIT -ne 0 ]; then
                    echo -e "\n❌ Dry run tests failed with exit code $TEST_EXIT"
                    exit $TEST_EXIT
                  else
                    echo -e "\n✅ Dry run tests passed!"
                  fi
                '';
              }
              {
                name = "test-with-server";
                category = "testing";
                help = "Run tests with an existing server";
                command = ''
                  echo "Running tests using existing server..."
                  source .venv/bin/activate
                  
                  # Check if pytest is installed
                  if ! python -c "import pytest" 2>/dev/null; then
                    echo "⚠️  pytest not found, installing..."
                    pip install pytest types-requests
                  fi
                  
                  # Check if server is running
                  if ! curl -s http://localhost:8000/docs -o /dev/null; then
                    echo -e "\n❌ ERROR: Server is not running!"
                    echo "Please start the server with 'run' command first"
                    exit 1
                  fi
                  
                  # Run tests with existing server
                  echo "Starting tests with existing server..."
                  python -m pytest -xvs test_mcp.py
                  TEST_EXIT=$?
                  
                  # Report test result
                  if [ $TEST_EXIT -ne 0 ]; then
                    echo -e "\n❌ Tests failed with exit code $TEST_EXIT"
                    exit $TEST_EXIT
                  else
                    echo -e "\n✅ All tests passed!"
                  fi
                '';
              }
              {
                name = "test-debug";
                category = "testing";
                help = "Run tests in debug mode";
                command = ''
                  echo "Running tests in debug mode..."
                  source .venv/bin/activate
                  python -u test_mcp.py --debug
                '';
              }
              {
                name = "lint";
                category = "development";
                help = "Lint Python code with Black";
                command = ''
                  echo "Linting Python code..."
                  source .venv/bin/activate
                  black server.py test_mcp.py
                '';
              }
              {
                name = "typecheck";
                category = "development";
                help = "Type check Python code with mypy";
                command = ''
                  echo "Type checking Python code..."
                  source .venv/bin/activate
                  mypy server.py test_mcp.py
                '';
              }
            ];
            
            # Define startup hook to create/activate venv
            devshell.startup.venv_setup.text = ''
              # Check if .venv exists and create it if needed
              if [ ! -d .venv ]; then
                echo "Creating Python virtual environment..."
                ${pythonEnv}/bin/python -m venv .venv
                source .venv/bin/activate
                pip install "mcp>=1.4.0" fastapi uvicorn requests
              else
                source .venv/bin/activate
              fi
              
              # Print environment info
              echo ""
              echo "┌─────────────────────────────────────────────────┐"
              echo "│            NixMCP Development Environment        │"
              echo "└─────────────────────────────────────────────────┘"
              echo ""
              echo "• Python: $(python --version)"
              echo "• Nix:    $(nix --version)"
              echo ""
              echo "┌─────────────────────────────────────────────────┐"
              echo "│                 Quick Commands                   │"
              echo "└─────────────────────────────────────────────────┘"
              echo ""
              echo "  ⚡ run       - Start the NixMCP server"
              echo "  🧪 test      - Run tests (requires server)"
              echo "  🧪 test-dry  - Run test mocks (no server needed)"
              echo "  🧹 lint      - Format code with Black"
              echo "  🔍 typecheck - Run mypy type checking"
              echo "  🔧 setup     - Set up Python environment"
              echo ""
              echo "Use 'menu' to see all available commands."
              echo "─────────────────────────────────────────────────────"
            '';
          };
          
          # Legacy devShell for backward compatibility
          legacy = pkgs.mkShell {
            name = "nixmcp-dev-legacy";
            
            packages = [
              # Python environment
              pythonEnv
              
              # Required Nix tools
              pkgs.nix
              pkgs.nixos-option
              
              # Our setup script
              setupScript
            ];
            
            # Standard shell hook for simple environment setup
            shellHook = ''
              # Ensure we use bash
              export SHELL=${pkgs.bash}/bin/bash
              
              # Clean up environment variables that might interfere
              unset SOURCE_DATE_EPOCH
              
              # Set a minimal prompt that won't have formatting issues
              export PS1="(nixmcp) $ "
              
              # Run our setup script
              setup-env
              
              # Activate the virtual environment
              source .venv/bin/activate
            '';
          };
        };
      });
}