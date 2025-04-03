"use client";

import Link from 'next/link';

export default function ClientFooter() {
  return (
    <footer className="bg-gray-100 py-12">
      <div className="container-custom mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          {/* Column 1 - About */}
          <div>
            <h3 className="text-lg font-semibold mb-4">MCP-NixOS</h3>
            <p className="text-gray-600 mb-4">
              Model Context Protocol resources and tools for NixOS, Home Manager, and nix-darwin.
            </p>
          </div>

          {/* Column 2 - Documentation */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Documentation</h3>
            <ul className="space-y-2 text-gray-600">
              <li>
                <Link href="/docs" className="hover:text-nix-primary">
                  Getting Started
                </Link>
              </li>
              <li>
                <Link href="/docs" className="hover:text-nix-primary">
                  API Reference
                </Link>
              </li>
              <li>
                <Link href="/docs" className="hover:text-nix-primary">
                  Configuration
                </Link>
              </li>
            </ul>
          </div>

          {/* Column 3 - Resources */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Resources</h3>
            <ul className="space-y-2 text-gray-600">
              <li>
                <a 
                  href="https://github.com/utensils/mcp-nixos"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub Repository
                </a>
              </li>
              <li>
                <a 
                  href="https://nixos.org"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  NixOS
                </a>
              </li>
              <li>
                <a 
                  href="https://github.com/nix-community/home-manager"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Home Manager
                </a>
              </li>
            </ul>
          </div>

          {/* Column 4 - Connect */}
          <div>
            <h3 className="text-lg font-semibold mb-4">Connect</h3>
            <ul className="space-y-2 text-gray-600">
              <li>
                <a 
                  href="https://github.com/utensils/mcp-nixos/issues"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Report Issues
                </a>
              </li>
              <li>
                <a 
                  href="https://github.com/utensils/mcp-nixos/pulls"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Pull Requests
                </a>
              </li>
              <li>
                <a 
                  href="https://github.com/utensils/mcp-nixos/discussions"
                  className="hover:text-nix-primary"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Discussions
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Copyright */}
        <div className="mt-8 pt-8 border-t border-gray-200 text-center text-gray-500">
          <p>© {new Date().getFullYear()} MCP-NixOS. MIT License.</p>
          <p className="mt-2 text-sm">
            <Link href="/images/attribution.md" className="hover:text-nix-primary">
              Logo Attribution
            </Link>
          </p>
        </div>
      </div>
    </footer>
  );
}