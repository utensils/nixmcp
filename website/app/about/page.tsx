import Link from 'next/link';

export default function AboutPage() {
  return (
    <div className="py-12">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8">About MCP-NixOS</h1>
        
        <div className="prose prose-lg max-w-none">
          <h2 className="text-2xl font-bold mt-8 mb-4">Project Overview</h2>
          <p className="mb-6">
            MCP-NixOS provides MCP (Model Context Protocol) resources and tools for NixOS packages, 
            system options, Home Manager configuration, and nix-darwin macOS configuration. It enables 
            AI assistants like Claude to understand and work with NixOS and related ecosystem tools.
          </p>
          
          <p className="mb-6">
            Communication uses JSON-based messages over standard I/O, making it compatible with 
            various AI assistants and applications. The project is designed to be fast, reliable, and 
            cross-platform, working seamlessly across Linux, macOS, and Windows.
          </p>
          
          <h2 className="text-2xl font-bold mt-10 mb-4">Core Components</h2>
          <ul className="list-disc pl-6 mb-8 space-y-2">
            <li><strong>Cache:</strong> Simple in-memory and filesystem HTML caching</li>
            <li><strong>Clients:</strong> Elasticsearch, Home Manager, nix-darwin, HTML</li>
            <li><strong>Contexts:</strong> Application state management for each platform</li>
            <li><strong>Resources:</strong> MCP resource definitions using URL schemes</li>
            <li><strong>Tools:</strong> Search, info, and statistics tools</li>
            <li><strong>Utils:</strong> Cross-platform helpers and cache management</li>
            <li><strong>Server:</strong> FastMCP server implementation</li>
            <li><strong>Pre-Cache:</strong> Command-line option to populate cache data during setup/build</li>
          </ul>
          
          <h2 className="text-2xl font-bold mt-10 mb-4">Project Goals</h2>
          <p className="mb-6">
            MCP-NixOS aims to make the NixOS ecosystem more accessible to users through AI assistance. 
            By providing structured access to package information, configuration options, and documentation, 
            it helps bridge the gap between NixOS's powerful but complex ecosystem and users of all skill levels.
          </p>
          
          <h2 className="text-2xl font-bold mt-10 mb-4">Contributing</h2>
          <p className="mb-6">
            MCP-NixOS is an open-source project and welcomes contributions. The default development branch is <code>develop</code>, 
            and the main release branch is <code>main</code>. Pull requests should follow the pattern: 
            commit to <code>develop</code> → open PR to <code>main</code> → merge once approved.
          </p>
          
          <div className="mt-8 flex space-x-4">
            <Link href="https://github.com/utensils/mcp-nixos" className="btn-primary">
              GitHub Repository
            </Link>
            <Link href="https://github.com/utensils/mcp-nixos/issues" className="btn-secondary">
              Report Issues
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}