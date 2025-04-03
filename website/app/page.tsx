import Link from 'next/link';
import FeatureCard from '@/components/FeatureCard';
import CodeBlock from '@/components/CodeBlock';

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Hero Section */}
      <section className="bg-gradient-to-b from-nix-primary to-nix-dark text-white py-20">
        <div className="container-custom text-center">
          <h1 className="text-4xl md:text-6xl font-bold mb-6">MCP-NixOS</h1>
          <p className="text-xl md:text-2xl mb-8 max-w-3xl mx-auto">
            Model Context Protocol resources and tools for NixOS, Home Manager, and nix-darwin
          </p>
          <div className="flex flex-col md:flex-row gap-4 justify-center">
            <Link href="/docs" className="btn-primary bg-white text-nix-primary hover:bg-nix-light">
              Get Started
            </Link>
            <Link href="https://github.com/utensils/mcp-nixos" className="btn-secondary bg-transparent text-white border-white hover:bg-white/10">
              GitHub
            </Link>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 bg-white">
        <div className="container-custom">
          <h2 className="text-3xl font-bold text-center mb-12">Key Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
            <FeatureCard 
              title="NixOS Packages & Options" 
              description="Search and retrieve detailed information about NixOS packages and system options."
              iconName="package"
            />
            <FeatureCard 
              title="Home Manager Integration" 
              description="Comprehensive support for Home Manager configuration options and hierarchical searches."
              iconName="home"
            />
            <FeatureCard 
              title="nix-darwin Support" 
              description="Access to nix-darwin macOS configuration options and resources."
              iconName="apple"
            />
            <FeatureCard 
              title="Fast & Efficient" 
              description="Multi-level caching with filesystem persistence for optimal performance."
              iconName="bolt"
            />
            <FeatureCard 
              title="Cross-Platform" 
              description="Works seamlessly across Linux, macOS, and Windows environments."
              iconName="globe"
            />
            <FeatureCard 
              title="Claude Integration" 
              description="Perfect compatibility with Claude and other AI assistants via the MCP protocol."
              iconName="robot"
            />
          </div>
        </div>
      </section>

      {/* Getting Started Section */}
      <section className="py-16 bg-nix-light">
        <div className="container-custom">
          <h2 className="text-3xl font-bold text-center mb-12">Getting Started</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12">
            <div>
              <h3 className="text-2xl font-bold mb-4">Installation</h3>
              <p className="mb-6">
                You can install MCP-NixOS using pip, uv, or add it to your Claude configuration:
              </p>
              <CodeBlock code="pip install mcp-nixos" language="bash" />
              <CodeBlock code="uv pip install mcp-nixos" language="bash" />
              <p className="mt-6">
                Or use Docker:
              </p>
              <CodeBlock code="docker run --rm ghcr.io/utensils/mcp-nixos" language="bash" />
            </div>
            <div>
              <h3 className="text-2xl font-bold mb-4">Configuration</h3>
              <p className="mb-6">
                Add to your Claude Code configuration file:
              </p>
              <CodeBlock 
                code={`{
  "tools": [
    {
      "path": "mcp-nixos",
      "enabled": true
    }
  ]
}`} 
                language="json" 
              />
              <p className="mt-6">
                Then start asking Claude about NixOS packages and configuration options!
              </p>
            </div>
          </div>
          <div className="text-center mt-12">
            <Link href="/docs" className="btn-primary">
              View Full Documentation
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}