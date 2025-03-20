{
  description = "NixMCP - Model Context Protocol server for NixOS resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        
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
            pip install "mcp>=1.4.0" fastapi uvicorn
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
        devShells.default = pkgs.mkShell {
          name = "nixmcp-dev";
          
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
      });
}