import CodeBlock from '@/components/CodeBlock';

export default function DocsPage() {
  return (
    <div className="py-12">
      <div className="container-custom">
        <h1 className="text-4xl font-bold mb-8">Documentation</h1>
        
        <div className="prose prose-lg max-w-none">
          <h2 className="text-2xl font-bold mt-8 mb-4">API Reference</h2>
          
          <div className="mb-12">
            <h3 className="text-xl font-bold mt-6 mb-3">NixOS Resources & Tools</h3>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Status, package info/search, option info/search, program search</li>
              <li><code>nixos_search()</code>, <code>nixos_info()</code>, <code>nixos_stats()</code></li>
              <li>Multiple channels: unstable (default), stable (24.11)</li>
            </ul>
            
            <h4 className="text-lg font-semibold mt-4 mb-2">Example: Search for a package</h4>
            <CodeBlock
              code={`{
  "type": "call",
  "tool": "nixos_search",
  "params": {
    "query": "python",
    "limit": 10,
    "channel": "unstable" 
  }
}`}
              language="json"
            />
          </div>
          
          <div className="mb-12">
            <h3 className="text-xl font-bold mt-6 mb-3">Home Manager Resources & Tools</h3>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Status, option info/search, hierarchical lists, prefix paths</li>
              <li><code>home_manager_search()</code>, <code>home_manager_info()</code>, <code>home_manager_options_by_prefix()</code></li>
            </ul>
            
            <h4 className="text-lg font-semibold mt-4 mb-2">Example: Get options by prefix</h4>
            <CodeBlock
              code={`{
  "type": "call",
  "tool": "home_manager_options_by_prefix",
  "params": {
    "option_prefix": "programs.git"
  }
}`}
              language="json"
            />
          </div>
          
          <div className="mb-12">
            <h3 className="text-xl font-bold mt-6 mb-3">nix-darwin Resources & Tools</h3>
            <ul className="list-disc pl-6 mb-4 space-y-2">
              <li>Status, option info/search, category lists, prefix paths</li>
              <li><code>darwin_search()</code>, <code>darwin_info()</code>, <code>darwin_options_by_prefix()</code></li>
            </ul>
            
            <h4 className="text-lg font-semibold mt-4 mb-2">Example: Search for darwin options</h4>
            <CodeBlock
              code={`{
  "type": "call",
  "tool": "darwin_search",
  "params": {
    "query": "keyboard",
    "limit": 5
  }
}`}
              language="json"
            />
          </div>
          
          <h2 className="text-2xl font-bold mt-10 mb-4">Configuration</h2>
          <p className="mb-4">MCP-NixOS can be configured through environment variables:</p>
          
          <div className="overflow-x-auto mb-8">
            <table className="min-w-full border-collapse border border-gray-300">
              <thead>
                <tr className="bg-gray-100">
                  <th className="border border-gray-300 px-4 py-2 text-left">Variable</th>
                  <th className="border border-gray-300 px-4 py-2 text-left">Description</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-mono text-sm">MCP_NIXOS_LOG_LEVEL</td>
                  <td className="border border-gray-300 px-4 py-2">Logging level (DEBUG, INFO, WARNING, ERROR)</td>
                </tr>
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-mono text-sm">MCP_NIXOS_LOG_FILE</td>
                  <td className="border border-gray-300 px-4 py-2">Path to log file</td>
                </tr>
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-mono text-sm">MCP_NIXOS_CACHE_DIR</td>
                  <td className="border border-gray-300 px-4 py-2">Directory for cache files</td>
                </tr>
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-mono text-sm">MCP_NIXOS_CACHE_TTL</td>
                  <td className="border border-gray-300 px-4 py-2">Cache time-to-live in seconds</td>
                </tr>
                <tr>
                  <td className="border border-gray-300 px-4 py-2 font-mono text-sm">ELASTICSEARCH_URL</td>
                  <td className="border border-gray-300 px-4 py-2">Custom Elasticsearch URL</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}