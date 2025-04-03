
export default function AboutPage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8 text-nix-dark">About MCP-NixOS</h1>
        
        <div className="prose prose-lg max-w-none">
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Project Overview</h2>
            <p className="mb-6 text-gray-800">
              MCP-NixOS provides MCP (Model Context Protocol) resources and tools for NixOS packages, 
              system options, Home Manager configuration, and nix-darwin macOS configuration. It enables 
              AI assistants like Claude to understand and work with NixOS and related ecosystem tools.
            </p>
            
            <p className="mb-6 text-gray-800">
              Communication uses JSON-based messages over standard I/O, making it compatible with 
              various AI assistants and applications. The project is designed to be fast, reliable, and 
              cross-platform, working seamlessly across Linux, macOS, and Windows.
            </p>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Core Components</h2>
            <ul className="grid gap-3 mb-6">
              {[
                { name: 'Cache', description: 'Simple in-memory and filesystem HTML caching' },
                { name: 'Clients', description: 'Elasticsearch, Home Manager, nix-darwin, HTML' },
                { name: 'Contexts', description: 'Application state management for each platform' },
                { name: 'Resources', description: 'MCP resource definitions using URL schemes' },
                { name: 'Tools', description: 'Search, info, and statistics tools' },
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
            <h2 className="text-2xl font-bold mb-6 text-nix-primary border-b border-nix-light pb-2">Project Goals</h2>
            <p className="mb-6 text-gray-800">
              MCP-NixOS aims to make the NixOS ecosystem more accessible to users through AI assistance. 
              By providing structured access to package information, configuration options, and documentation, 
              it helps bridge the gap between NixOS&apos;s powerful but complex ecosystem and users of all skill levels.
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
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}