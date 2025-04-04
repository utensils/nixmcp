import CodeBlock from '@/components/CodeBlock';
import AnchorHeading from '@/components/AnchorHeading';

export default function DocsPage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <AnchorHeading level={1} className="text-4xl font-bold mb-8 text-nix-dark">Documentation</AnchorHeading>
        
        <div className="prose prose-lg max-w-none">
          <AnchorHeading level={2} className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2">API Reference</AnchorHeading>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">NixOS Resources & Tools</AnchorHeading>
            <ul className="grid gap-3 mb-6">
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-800">Status, package info/search, option info/search, program search</span>
              </li>
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                  nixos_search()
                </span>
                <span className="mx-2 text-gray-500">|</span>
                <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                  nixos_info()
                </span>
                <span className="mx-2 text-gray-500">|</span>
                <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                  nixos_stats()
                </span>
              </li>
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-800">Multiple channels: <span className="font-medium">unstable</span> (default), <span className="font-medium">stable</span> (24.11)</span>
              </li>
            </ul>
            
            <div className="mt-6">
              <AnchorHeading level={4} className="text-lg font-semibold mb-3 text-nix-primary flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                Example: Search for a package
              </AnchorHeading>
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
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">Home Manager Resources & Tools</AnchorHeading>
            <ul className="grid gap-3 mb-6">
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-800">Status, option info/search, hierarchical lists, prefix paths</span>
              </li>
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    home_manager_search()
                  </span>
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    home_manager_info()
                  </span>
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    home_manager_options_by_prefix()
                  </span>
                </div>
              </li>
            </ul>
            
            <div className="mt-6">
              <AnchorHeading level={4} className="text-lg font-semibold mb-3 text-nix-primary flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                Example: Get options by prefix
              </AnchorHeading>
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
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">nix-darwin Resources & Tools</AnchorHeading>
            <ul className="grid gap-3 mb-6">
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <span className="text-gray-800">Status, option info/search, category lists, prefix paths</span>
              </li>
              <li className="flex items-start">
                <span className="inline-block w-2 h-2 rounded-full bg-nix-primary mt-2 mr-3 flex-shrink-0"></span>
                <div className="flex flex-wrap gap-2 items-center">
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    darwin_search()
                  </span>
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    darwin_info()
                  </span>
                  <span className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">
                    darwin_options_by_prefix()
                  </span>
                </div>
              </li>
            </ul>
            
            <div className="mt-6">
              <AnchorHeading level={4} className="text-lg font-semibold mb-3 text-nix-primary flex items-center">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
                </svg>
                Example: Search for darwin options
              </AnchorHeading>
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
          </section>
          
          <AnchorHeading level={2} className="text-2xl font-bold mt-12 mb-6 text-nix-primary border-b border-nix-light pb-2">Configuration</AnchorHeading>
          <p className="mb-6 text-gray-800 font-medium">MCP-NixOS can be configured through environment variables:</p>
          
          <div className="overflow-x-auto mb-12 rounded-lg shadow-sm">
            <table className="min-w-full border-collapse">
              <thead>
                <tr className="bg-nix-primary">
                  <th className="px-6 py-3 text-left text-white font-semibold rounded-tl-lg">Variable</th>
                  <th className="px-6 py-3 text-left text-white font-semibold rounded-tr-lg">Description</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                  <td className="px-6 py-4 font-mono text-sm font-semibold text-nix-dark">MCP_NIXOS_LOG_LEVEL</td>
                  <td className="px-6 py-4 text-gray-700">Logging level (DEBUG, INFO, WARNING, ERROR)</td>
                </tr>
                <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                  <td className="px-6 py-4 font-mono text-sm font-semibold text-nix-dark">MCP_NIXOS_LOG_FILE</td>
                  <td className="px-6 py-4 text-gray-700">Path to log file</td>
                </tr>
                <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                  <td className="px-6 py-4 font-mono text-sm font-semibold text-nix-dark">MCP_NIXOS_CACHE_DIR</td>
                  <td className="px-6 py-4 text-gray-700">Directory for cache files</td>
                </tr>
                <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                  <td className="px-6 py-4 font-mono text-sm font-semibold text-nix-dark">MCP_NIXOS_CACHE_TTL</td>
                  <td className="px-6 py-4 text-gray-700">Cache time-to-live in seconds</td>
                </tr>
                <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                  <td className="px-6 py-4 font-mono text-sm font-semibold text-nix-dark rounded-bl-lg">ELASTICSEARCH_URL</td>
                  <td className="px-6 py-4 text-gray-700 rounded-br-lg">Custom Elasticsearch URL</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}