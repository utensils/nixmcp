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
        # Configuration variables
        pythonVersion = "311";
        defaultPort = "8080";
        
        # Import nixpkgs with overlays
        pkgs = import nixpkgs { 
          inherit system; 
          overlays = [ 
            devshell.overlays.default
          ];
        };
        
        # Create a Python environment with base dependencies
        python = pkgs."python${pythonVersion}";
        pythonEnv = python.withPackages (ps: with ps; [
          pip
          setuptools
          wheel
          # Note: venv is built into Python, not a separate package
        ]);
        
        # Create a reusable uv installer derivation
        uvInstaller = pkgs.stdenv.mkDerivation {
          name = "uv-installer";
          buildInputs = [];
          unpackPhase = "true";
          installPhase = ''
            mkdir -p $out/bin
            echo '#!/usr/bin/env bash' > $out/bin/install-uv
            echo 'if ! command -v uv >/dev/null 2>&1; then' >> $out/bin/install-uv
            echo '  echo "Installing uv for faster Python package management..."' >> $out/bin/install-uv
            echo '  curl -LsSf https://astral.sh/uv/install.sh | sh' >> $out/bin/install-uv
            echo 'else' >> $out/bin/install-uv
            echo '  echo "uv is already installed."' >> $out/bin/install-uv
            echo 'fi' >> $out/bin/install-uv
            chmod +x $out/bin/install-uv
          '';
        };
        
        # Unified venv setup function
        setupVenvScript = ''
          if [ ! -d .venv ]; then
            echo "Creating Python virtual environment..."
            ${pythonEnv}/bin/python -m venv .venv
            source .venv/bin/activate
            
            # Check if uv is available and use it, otherwise fall back to pip
            if command -v uv >/dev/null 2>&1; then
              echo "Using uv to install dependencies..."
              uv pip install -r requirements.txt
            else
              echo "Using pip to install dependencies..."
              pip install -r requirements.txt
            fi
          else
            source .venv/bin/activate
          fi
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
              { name = "DEFAULT_PORT"; value = "${defaultPort}"; }
            ];
            
            packages = with pkgs; [
              # Python environment
              pythonEnv
              
              # Required Nix tools
              nix
              nixos-option
              
              # Development tools
              black
              (pkgs."python${pythonVersion}Packages".pytest)
              
              # uv installer tool
              uvInstaller
            ];
            
            # Startup commands
            commands = [
              {
                name = "setup";
                category = "development";
                help = "Set up Python environment and install dependencies";
                command = ''
                  echo "Setting up Python virtual environment..."
                  ${setupVenvScript}
                  echo "✓ Setup complete!"
                '';
              }
              {
                name = "setup-uv";
                category = "development";
                help = "Install uv for faster Python package management";
                command = ''
                  if ! command -v uv >/dev/null 2>&1; then
                    echo "Installing uv for faster Python package management..."
                    curl -LsSf https://astral.sh/uv/install.sh | sh
                    echo "✓ uv installed successfully!"
                    echo "Run 'setup' again to use uv for dependency installation"
                  else
                    echo "✓ uv is already installed"
                  fi
                '';
              }
              {
                name = "run";
                category = "server";
                help = "Run the NixMCP server";
                command = ''
                  echo "Starting NixMCP server..."
                  source .venv/bin/activate
                  
                  # Default port from environment
                  PORT=$DEFAULT_PORT
                  
                  # Parse arguments to extract port if specified
                  for arg in "$@"; do
                    case $arg in
                      --port=*)
                        PORT=''${arg#*=}
                        shift
                        ;;
                      *)
                        # Unknown option
                        ;;
                    esac
                  done
                  
                  echo "Starting server (port: $PORT)"
                  python server.py --port $PORT
                '';
              }
              {
                name = "run-tests";
                category = "testing";
                help = "Run tests";
                command = ''
                  echo "Running tests..."
                  source .venv/bin/activate
                  
                  # Placeholder for tests
                  echo "TODO: Implement tests"
                '';
              }
              {
                name = "lint";
                category = "development";
                help = "Lint Python code with Black";
                command = ''
                  echo "Linting Python code..."
                  source .venv/bin/activate
                  black *.py
                '';
              }
            ];
            
            # Define startup hook to create/activate venv
            devshell.startup.venv_setup.text = ''
              # Set up virtual environment
              ${setupVenvScript}
              
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
              echo "  ⚡ run        - Start the NixMCP server"
              echo "  🧪 run-tests  - Run tests"
              echo "  🧹 lint       - Format code with Black"
              echo "  🔧 setup      - Set up Python environment"
              echo "  🚀 setup-uv   - Install uv for faster dependency management"
              echo ""
              echo "Use 'menu' to see all available commands."
              echo "─────────────────────────────────────────────────────"
            '';
          };
          
          # Legacy devShell for backward compatibility (simplified)
          legacy = pkgs.mkShell {
            name = "nixmcp-legacy";
            
            packages = [
              pythonEnv
              pkgs.nix
              pkgs.nixos-option
              uvInstaller
            ];
            
            # Simple shell hook that uses the same setup logic
            shellHook = ''
              export SHELL=${pkgs.bash}/bin/bash
              export PS1="(nixmcp) $ "
              
              # Set up virtual environment
              ${setupVenvScript}
              
              echo "NixMCP Legacy Shell activated"
              echo "Run 'python server.py' to start the server"
            '';
          };
        };
      });
}