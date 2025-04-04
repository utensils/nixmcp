import AnchorHeading from '@/components/AnchorHeading';
import CodeBlock from '@/components/CodeBlock';
import CollapsibleSection from '@/components/CollapsibleSection';
import Link from 'next/link';

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
                This configuration enables your AI assistant to access NixOS package information and configuration options through the MCP protocol. For additional configuration options, see the <Link href="/docs#configuration" className="text-nix-primary hover:text-nix-dark underline transition-colors">configuration documentation</Link>.
              </p>
            </div>
          </div>

          <AnchorHeading
            level={2}
            className="text-2xl font-bold mt-8 mb-6 text-nix-primary border-b border-nix-light pb-2"
          >
            Example Scenarios
          </AnchorHeading>

          <div className="space-y-8">
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

            <p className="text-gray-700 mb-6 leading-relaxed">
              These examples demonstrate practical use cases for MCP-NixOS tools and the type of
              information they provide. Each example shows the complete workflow from user question to AI response.
            </p>

            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;What PostgreSQL versions are available in NixOS, and what are the
                configuration options?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for PostgreSQL Packages">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS search for packages",
  "type": "packages",
  "limit": 10,
  "query": "postgresql"
}
Found 10 packages matching 'postgresql':

- postgresql_13 (13.14)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_14 (14.10)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_15 (15.5)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_16 (16.1)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql_17 (17.0)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql (16.1)
  PostgreSQL is a powerful, open source object-relational database system

- postgresql-unit (7.11.0)
  SI Units for PostgreSQL

- postgresql_jdbc (42.6.1)
  JDBC driver for PostgreSQL allowing Java programs to connect to a PostgreSQL database

- postgresql17JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications

- postgresql14JitPackages.lantern (0.5.0)
  PostgreSQL vector database extension for building AI applications`}
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get PostgreSQL Service Options">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS info for option",
  "type": "option",
  "name": "services.postgresql"
}
# services.postgresql

**Description:** PostgreSQL database server.

**Type:** option set

**Declared by:**
- nixpkgs/nixos/modules/services/databases/postgresql.nix

**Default value:** {}

**Example:**
\`\`\`nix
{
  services.postgresql = {
    enable = true;
    package = pkgs.postgresql_14;
    enableTCPIP = true;
    authentication = pkgs.lib.mkOverride 10 ''
      local all all trust
      host all all 127.0.0.1/32 trust
      host all all ::1/128 trust
    '';
    initialScript = pkgs.writeText "backend-initScript" ''
      CREATE ROLE nixcloud WITH LOGIN PASSWORD 'nixcloud' CREATEDB;
      CREATE DATABASE nixcloud;
      GRANT ALL PRIVILEGES ON DATABASE nixcloud TO nixcloud;
    '';
  };
}
\`\`\`

**Option: services.postgresql.authentication** (strings concatenated with "\\n")
Defines how users authenticate when connecting to the database. See the
documentation for pg_hba.conf for details on the expected format of
this option. By default, peer based authentication will be used for
users connecting via the Unix socket, and md5 password authentication
will be used for users connecting via TCP. Any added rules will be
inserted above the default rules. If you'd like to replace the default
rules entirely, you can use \`lib.mkForce\` in your module.

**Type:** strings concatenated with "\\n"

**Option: services.postgresql.dataDir** (absolute path)
  The data directory for PostgreSQL.
**Option: services.postgresql.enable** (boolean)
  Whether to enable PostgreSQL Server.
**Option: services.postgresql.enableJIT** (boolean)
  Whether to enable JIT support.
**Option: services.postgresql.enableTCPIP** (boolean)
  Whether PostgreSQL should listen on all network interfaces.`}
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  AI Assistant Response:
                </h5>
                <p className="text-gray-700">
                  NixOS provides multiple versions of PostgreSQL:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>PostgreSQL 13 (13.14)</li>
                  <li>PostgreSQL 14 (14.10)</li>
                  <li>PostgreSQL 15 (15.5)</li>
                  <li>PostgreSQL 16 (16.1) - This is the default version</li>
                  <li>PostgreSQL 17 (17.0) - Latest version</li>
                </ul>
                <p className="text-gray-700 mt-2">
                  For configuration, you can use the <code className="font-mono text-xs">services.postgresql</code> module with these key options:
                </p>
                <ul className="list-disc list-inside mt-1 text-gray-700 space-y-1">
                  <li>
                    <code className="font-mono text-xs">enable</code> - Enable the PostgreSQL server
                  </li>
                  <li>
                    <code className="font-mono text-xs">package</code> - Select which PostgreSQL version to use
                  </li>
                  <li>
                    <code className="font-mono text-xs">authentication</code> - Configure client authentication methods
                  </li>
                  <li>
                    <code className="font-mono text-xs">enableTCPIP</code> - Allow network connections (not just local socket)
                  </li>
                  <li>
                    <code className="font-mono text-xs">dataDir</code> - Specify where to store the database files
                  </li>
                </ul>
                <p className="text-gray-700 mt-2">
                  This information helps system administrators choose the appropriate
                  PostgreSQL version and configure it according to their specific
                  requirements.
                </p>
              </div>
            </div>

            <div className="bg-nix-light bg-opacity-20 p-4 rounded-lg border border-nix-light mb-6">
              <h4 className="font-semibold text-nix-dark mb-3 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Example 2: Checking Package Availability
              </h4>
              <h4 className="font-semibold text-nix-dark mb-2 flex items-center">
                <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
                User Prompt
              </h4>
              <p className="text-gray-700 mb-4 italic">
                &quot;Is the tldr package available in NixOS, and what variants exist?&quot;
              </p>

              <CollapsibleSection title="Tool Call 1: Search for tldr Package">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS search for packages",
  "type": "packages",
  "limit": 10,
  "query": "tldr"
}
Found 6 packages matching 'tldr':

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
                  language="json"
                />
              </CollapsibleSection>

              <CollapsibleSection title="Tool Call 2: Get Detailed Package Information">
                <CodeBlock
                  code={`{
  "ctx": "Checking NixOS info for package",
  "type": "package",
  "name": "tldr"
}
# tldr

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
                  language="json"
                />
              </CollapsibleSection>

              <div className="bg-nix-light bg-opacity-30 p-4 rounded-lg border border-nix-light mt-4">
                <h5 className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                  <svg className="w-4 h-4 mr-2 text-nix-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
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
  );
}
