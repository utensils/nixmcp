
import Image from 'next/image';

export default function AboutPage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8 text-nix-dark">About MCP-NixOS</h1>
        
        <div className="prose prose-lg max-w-none">
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Project Overview</h2>
            <p className="mb-6 text-gray-800">
              MCP-NixOS is a Model Context Protocol server that provides accurate information about NixOS packages and configuration options.
              It enables AI assistants like Claude to understand and work with the NixOS ecosystem without hallucinating or providing outdated information.
            </p>
            
            <p className="mb-6 text-gray-800">
              It provides real-time access to:
            </p>
            <ul className="grid gap-3 mb-6">
              {[
                'NixOS packages with accurate metadata',
                'System configuration options',
                'Home Manager settings for user-level configuration',
                'nix-darwin macOS configuration options'
              ].map((item, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span className="text-gray-800">{item}</span>
                </li>
              ))}
            </ul>
            <p className="mb-6 text-gray-800">
              Communication uses JSON-based messages over standard I/O, making it compatible with 
              various AI assistants and applications. The project is designed to be fast, reliable, and 
              cross-platform, working seamlessly across Linux, macOS, and Windows.
            </p>
            
            <div className="mt-8 p-4 bg-white rounded-lg border border-gray-200">
              <div className="flex items-center mb-2">
                <Image 
                  src="/images/utensils-logo.png" 
                  alt="Utensils Logo" 
                  width={36} 
                  height={36} 
                  className="mr-2" 
                />
                <h3 className="font-semibold text-nix-dark">Utensils Project</h3>
              </div>
              <p className="text-gray-700">
                MCP-NixOS is developed and maintained by <a href="https://utensils.io" target="_blank" rel="noopener noreferrer" className="text-nix-primary hover:underline">Utensils</a>, 
                an organization focused on creating high-quality tools and utilities for developers and system engineers.
              </p>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Core Components</h2>
            <ul className="grid gap-3 mb-6">
              {[
                { name: 'Cache', description: 'In-memory and filesystem HTML caching with TTL-based expiration' },
                { name: 'Clients', description: 'Elasticsearch API and HTML documentation parsers' },
                { name: 'Contexts', description: 'Application state management for each platform' },
                { name: 'Resources', description: 'MCP resource definitions using URL schemes' },
                { name: 'Tools', description: 'Search, info, and statistics tools with multiple channel support' },
                { name: 'Utils', description: 'Cross-platform helpers and cache management' },
                { name: 'Server', description: 'FastMCP server implementation' },
                { name: 'Pre-Cache', description: 'Command-line option to populate cache data during setup/build' }
              ].map((component, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span>
                    <span className="font-semibold text-nix-dark">{component.name}:</span>{' '}
                    <span className="text-gray-800">{component.description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Features</h2>
            <ul className="grid gap-3 mb-6">
              {[
                { name: 'NixOS Resources', description: 'Packages and system options via Elasticsearch API with multiple channel support (unstable, stable/24.11)' },
                { name: 'Home Manager', description: 'User configuration options via parsed documentation with hierarchical paths' },
                { name: 'nix-darwin', description: 'macOS configuration options for system defaults, services, and settings' },
                { name: 'Smart Caching', description: 'Reduces network requests, improves startup time, and works offline once cached' },
                { name: 'Rich Search', description: 'Fast in-memory search with related options for better discovery' }
              ].map((feature, index) => (
                <li key={index} className="flex items-start">
                  <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                  <span>
                    <span className="font-semibold text-nix-dark">{feature.name}:</span>{' '}
                    <span className="text-gray-800">{feature.description}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">What is Model Context Protocol?</h2>
            <p className="mb-6 text-gray-800">
              The <a href="https://modelcontextprotocol.io" className="text-nix-primary hover:text-nix-dark" target="_blank" rel="noopener noreferrer">Model Context Protocol (MCP)</a> is an open protocol that connects LLMs to external data and tools using JSON messages over stdin/stdout. 
              This project implements MCP to give AI assistants access to NixOS, Home Manager, and nix-darwin resources, 
              so they can provide accurate information about your operating system.
            </p>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Contributing</h2>
            <p className="mb-6 text-gray-800">
              MCP-NixOS is an open-source project and welcomes contributions. The default development branch is{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">develop</code>, and the main release branch is{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">main</code>. Pull requests should follow the pattern: 
              commit to <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">develop</code> → open PR to{' '}
              <code className="bg-gray-100 px-1 py-0.5 rounded text-nix-dark">main</code> → merge once approved.
            </p>
            
            <div className="mt-8 flex flex-wrap gap-4">
              <a 
                href="https://github.com/utensils/mcp-nixos" 
                className="inline-block bg-nix-primary hover:bg-nix-dark text-white font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                GitHub Repository
              </a>
              <a 
                href="https://github.com/utensils/mcp-nixos/issues" 
                className="inline-block bg-white border-2 border-nix-primary hover:border-nix-dark text-nix-primary hover:text-nix-dark font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                Report Issues
              </a>
              <a 
                href="https://codecov.io/gh/utensils/mcp-nixos" 
                className="inline-block bg-white border-2 border-nix-primary hover:border-nix-dark text-nix-primary hover:text-nix-dark font-semibold py-2 px-6 rounded-lg transition-colors duration-200"
                target="_blank"
                rel="noopener noreferrer"
              >
                Code Coverage
              </a>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}