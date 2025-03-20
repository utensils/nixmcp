{
  description = "NixMCP - Model Context Protocol for NixOS resources";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = import nixpkgs { inherit system; };
        pythonEnv = pkgs.python311.withPackages (ps: with ps; [
          pytest
          black
          isort
          mypy
          # XML parsing for nixos-option output
          lxml
          # For rich terminal output
          rich
        ]);
      in
      {
        devShells.default = pkgs.mkShell {
          buildInputs = [
            pythonEnv
            pkgs.python311Packages.pip
            
            # Nix tools
            pkgs.nix
            pkgs.nixos-option  # If available - might need conditional inclusion
            
            # Development tools
            pkgs.git
          ];

          shellHook = ''
            echo "Welcome to NixMCP development environment!"
            echo "Python version: $(python --version)"
            echo "Nix version: $(nix --version)"
            
            # Check if nixos-option is available
            if command -v nixos-option >/dev/null 2>&1; then
              echo "nixos-option: available"
            else
              echo "nixos-option: not available (some functionality may be limited)"
            fi
          '';
        };
      });
}