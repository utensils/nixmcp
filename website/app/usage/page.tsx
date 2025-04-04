import AnchorHeading from '@/components/AnchorHeading';
import CodeBlock from '@/components/CodeBlock';

export default function UsagePage() {
  return (
    <div className="py-12 bg-white">
      <div className="container-custom">
        <AnchorHeading level={1} className="text-4xl font-bold mb-8 text-nix-dark">
          Usage Examples
        </AnchorHeading>

        <div className="prose prose-lg max-w-none">
          <AnchorHeading
            level={2}
            className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2"
          >
            Overview
          </AnchorHeading>

          <div className="bg-gradient-to-br from-nix-light to-white p-6 rounded-lg shadow-sm mb-8">
            <p className="text-gray-800 mb-6 leading-relaxed">
              These examples demonstrate how to use MCP-NixOS tools to solve common Nix ecosystem
              tasks. Each example shows the JSON request format and the corresponding response,
              helping you understand how to effectively leverage MCP-NixOS in your workflows.
            </p>
            
            <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5 mb-2">
              <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
                <svg className="w-5 h-5 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                Configuration
              </h3>
              <p className="mb-4 text-gray-700">
                Before using these examples, you&apos;ll need to configure your MCP server. Add the following to your MCP configuration file:
              </p>
              <CodeBlock 
                code={`{
  "mcpServers": {
    "nixos": {
      "command": "uvx",
      "args": ["mcp-nixos"]
    }
  }
}`} 
                language="json" 
              />
              <p className="mt-4 text-gray-700 text-sm">
                This configuration enables your AI assistant to access NixOS package information and configuration options through the MCP protocol.
              </p>
            </div>
          </div>

          <AnchorHeading
            level={2}
            className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2"
          >
            Usage Examples
          </AnchorHeading>

          <div className="space-y-6">


            <div className="bg-white rounded-lg shadow-sm border-l-4 border-nix-primary p-5 mb-6">
              <h3 className="text-xl font-semibold text-nix-dark mb-3 flex items-center">
                <svg
                  className="w-5 h-5 mr-2 text-nix-primary"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                    clipRule="evenodd"
                  />
                </svg>
                Example 1: PostgreSQL Versions and Configuration
              </h3>

              <p className="text-gray-700 mb-4">
                These examples demonstrate simple use cases for MCP-NixOS tools and the type of
                information they provide.
              </p>

              <div className="space-y-6">
                <div className="border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-nix-primary mb-2">User Prompt</h4>
                  <p className="text-gray-700 mb-3">
                    &quot;What PostgreSQL versions are available in NixOS, and what are the
                    configuration options?&quot;
                  </p>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Tool Call 1: Search for PostgreSQL Packages
                    </h5>
                    <CodeBlock
                      code={`{  
  "type": "call",
  "tool": "nixos_search",
  "params": {
    "query": "postgresql",
    "type": "packages",
    "limit": 10
  }
}`}
                      language="json"
                    />
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Available PostgreSQL Versions:
                    </h5>
                    <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                      <CodeBlock
                        code={`Found 10 packages matching 'postgresql':

- postgresql (17.4)
  Powerful, open source object-relational database system

- postgresql_15 (15.12)
  Powerful, open source object-relational database system

- postgresql_16 (16.8)
  Powerful, open source object-relational database system

- postgresql_14 (14.17)
  Powerful, open source object-relational database system

- postgresql_13 (13.20)
  Powerful, open source object-relational database system

- postgresql_jdbc (42.6.1)
  JDBC driver for PostgreSQL allowing Java programs to connect to a PostgreSQL database

- postgresql17JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications

- postgresql14JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications`}
                        language="markdown"
                      />
                    </div>
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Tool Call 2: Get PostgreSQL Service Options
                    </h5>
                    <CodeBlock
                      code={`{  
  "type": "call",
  "tool": "nixos_info",
  "params": {
    "name": "services.postgresql",
    "type": "option"
  }
}`}
                      language="json"
                    />
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      PostgreSQL Configuration Options:
                    </h5>
                    <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                      <CodeBlock
                        code={`# services.postgresql.authentication

**Description:** Defines how users authenticate themselves to the server. See the PostgreSQL
documentation for pg_hba.conf for details on the expected format of
this option. By default, peer based authentication will be used for
users connecting via the Unix socket, and md5 password authentication
will be used for users connecting via TCP. Any added rules will be
inserted above the default rules. If you'd like to replace the default
rules entirely, you can use \`lib.mkForce\` in your module.

**Type:** strings concatenated with "\n"
**Default:** \`""\`

## Related Options for postgresql Service

- \`services.postgresql.checkConfig\` (boolean)
  Check the syntax of the configuration file at compile time
- \`services.postgresql.dataDir\` (absolute path)
  The data directory for PostgreSQL.
- \`services.postgresql.enable\` (boolean)
  Whether to enable PostgreSQL Server.
- \`services.postgresql.enableJIT\` (boolean)
  Whether to enable JIT support.
- \`services.postgresql.enableTCPIP\` (boolean)
  Whether PostgreSQL should listen on all network interfaces.`}
                        language="markdown"
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 p-3 rounded-md border border-blue-200">
                    <h5 className="text-md font-semibold mb-1 text-blue-700">
                      AI Assistant Response:
                    </h5>
                    <p className="text-gray-700">
                      NixOS provides multiple PostgreSQL versions (13, 14, 15, 16, and 17) that
                      can be selected using the{' '}
                      <code className="font-mono text-xs">services.postgresql.package</code>{' '}
                      option. The default version is currently 17.4.
                    </p>
                    <p className="text-gray-700 mt-2">Key configuration options include:</p>
                    <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                      <li>
                        Authentication methods via{' '}
                        <code className="font-mono text-xs">
                          services.postgresql.authentication
                        </code>
                      </li>
                      <li>
                        Network listening control with{' '}
                        <code className="font-mono text-xs">
                          services.postgresql.enableTCPIP
                        </code>
                      </li>
                      <li>
                        Performance tuning with{' '}
                        <code className="font-mono text-xs">services.postgresql.enableJIT</code>
                      </li>
                      <li>
                        Data storage location via{' '}
                        <code className="font-mono text-xs">services.postgresql.dataDir</code>
                      </li>
                    </ul>
                    <p className="text-gray-700 mt-2">
                      This information helps system administrators choose the appropriate
                      PostgreSQL version and configure it according to their specific
                      requirements.
                    </p>
                  </div>
                </div>

                <div className="border border-gray-200 rounded-lg p-4 mt-6">
                  <h4 className="font-semibold text-nix-primary mb-2">
                    Example 2: Checking Package Availability
                  </h4>
                  <h4 className="font-semibold text-nix-primary mb-2">User Prompt</h4>
                  <p className="text-gray-700 mb-3">
                    &quot;Is the tldr package available in NixOS, and what variants exist?&quot;
                  </p>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Tool Call 1: Search for tldr Package
                    </h5>
                    <CodeBlock
                      code={`{  
  "type": "call",
  "tool": "nixos_search",
  "params": {
    "query": "tldr",
    "type": "packages",
    "limit": 10
  }
}`}
                      language="json"
                    />
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Search Results:
                    </h5>
                    <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                      <CodeBlock
                        code={`Found 6 packages matching 'tldr':

- tldr (3.3.0)
  Simplified and community-driven man pages

- haskellPackages.tldr (0.9.2)
  Haskell tldr client

- tlrc (1.11.0)
  Official tldr client written in Rust

- tealdeer (1.7.2)
  Very fast implementation of tldr in Rust

- emacsPackages.tldr (20230301.136)

- rPackages.tldr (0.4.0)`}
                        language="markdown"
                      />
                    </div>
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Tool Call 2: Get Detailed Package Information
                    </h5>
                    <CodeBlock
                      code={`{  
  "type": "call",
  "tool": "nixos_info",
  "params": {
    "name": "tldr",
    "type": "package"
  }
}`}
                      language="json"
                    />
                  </div>

                  <div className="mb-3">
                    <h5 className="text-md font-semibold mb-2 text-nix-dark">
                      Package Details:
                    </h5>
                    <div className="bg-gray-50 p-3 rounded-md border border-gray-200">
                      <CodeBlock
                        code={`# tldr

**Version:** 3.3.0

**Description:** Simplified and community-driven man pages

**Long Description:**
tldr pages gives common use cases for commands, so you don't need to
hunt through a man page for the correct flags.

**Homepage:** https://tldr.sh

**License:** MIT License

**Maintainers:** Taeer Bar-Yam, Carlos D'Agostino, K.B.Dharun Krishna

**Platforms:** Multiple platforms including Linux, macOS, Windows, and more

**Provided Programs:** tldr`}
                        language="markdown"
                      />
                    </div>
                  </div>

                  <div className="bg-blue-50 p-3 rounded-md border border-blue-200">
                    <h5 className="text-md font-semibold mb-1 text-blue-700">
                      AI Assistant Response:
                    </h5>
                    <p className="text-gray-700">
                      NixOS provides several implementations of the tldr client:
                    </p>
                    <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                      <li>
                        The main Python-based <code className="font-mono text-xs">tldr</code>{' '}
                        package
                      </li>
                      <li>
                        Rust implementations: <code className="font-mono text-xs">tlrc</code>{' '}
                        (official) and <code className="font-mono text-xs">tealdeer</code>{' '}
                        (optimized for speed)
                      </li>
                      <li>Language-specific implementations for Haskell, Emacs Lisp, and R</li>
                    </ul>
                    <p className="text-gray-700 mt-2">
                      The main package is available across multiple platforms and provides a
                      simple command-line interface for accessing community-maintained
                      simplified documentation. This is particularly useful for quickly finding
                      common usage examples without having to read through comprehensive man
                      pages.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}