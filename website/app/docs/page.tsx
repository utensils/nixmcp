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
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about NixOS packages, options, and programs.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">nixos_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for NixOS packages, options, or programs.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">type</code>: The type to search (&quot;packages&quot;, &quot;options&quot;, or &quot;programs&quot;) - default: &quot;packages&quot;</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Search for packages
              </AnchorHeading>
              <CodeBlock
                code={`{
  &quot;type&quot;: &quot;call&quot;,
  &quot;tool&quot;: &quot;nixos_search&quot;,
  &quot;params&quot;: {
    &quot;query&quot;: &quot;python&quot;,
    &quot;type&quot;: &quot;packages&quot;,
    &quot;limit&quot;: 10,
    &quot;channel&quot;: &quot;unstable&quot; 
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`Found 10 packages matching 'python':

- python2 (2.7.18.8)
  High-level dynamically-typed programming language

- python2Full (2.7.18.8)
  High-level dynamically-typed programming language

- python27Full (2.7.18.8)
  High-level dynamically-typed programming language

- python3Full (3.12.9)
  High-level dynamically-typed programming language

- python314 (3.14.0a6)
  High-level dynamically-typed programming language

- python39 (3.9.21)
  High-level dynamically-typed programming language

- python3Minimal (3.12.9)
  High-level dynamically-typed programming language

- python313Full (3.13.2)
  High-level dynamically-typed programming language

- python314Full (3.14.0a6)
  High-level dynamically-typed programming language

- texlivePackages.python (0.22)
  Embed Python code in LaTeX`}
                  language="text"

                />
              </div>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Search for options
              </AnchorHeading>
              <CodeBlock
                code={`{
  &quot;type&quot;: &quot;call&quot;,
  &quot;tool&quot;: &quot;nixos_search&quot;,
  &quot;params&quot;: {
    &quot;query&quot;: &quot;services.postgresql&quot;,
    &quot;type&quot;: &quot;options&quot;,
    &quot;channel&quot;: &quot;unstable&quot;
  }
}`}
                language="json"
              />
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a NixOS package or option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the package or option</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">type</code>: Either &quot;package&quot; or &quot;option&quot; - default: &quot;package&quot;</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get package info
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_info",
  "params": {
    "name": "python3Full",
    "type": "package",
    "channel": "unstable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# python3Full

**Version:** 3.12.9

**Description:** High-level dynamically-typed programming language

**Long Description:**
Python is a remarkably powerful dynamic programming language that is
used in a wide variety of application domains...

**Homepage:** https://www.python.org

**License:** Python Software Foundation License version 2

**Source:** [pkgs/development/interpreters/python/cpython/default.nix:803](https://github.com/NixOS/nixpkgs/blob/master/pkgs/development/interpreters/python/cpython/default.nix#L803)

**Maintainers:** Martin Weinelt, Tomoya Otabi

**Platforms:** mips64-linux, i686-freebsd, armv6l-linux, i686-cygwin, riscv64-linux, x86_64-darwin...

**Provided Programs:** 2to3, 2to3-3.12, idle, idle3, idle3.12, pydoc, pydoc3, pydoc3.12, python, python-config, python3, python3-config, python3.12, python3.12-config`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">nixos_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about available NixOS packages and options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">channel</code>: NixOS channel to use (&quot;unstable&quot; or &quot;24.11&quot;) - default: &quot;unstable&quot;</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get NixOS stats
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "nixos_stats",
  "params": {
    "channel": "unstable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# NixOS Statistics (Channel: unstable)

Total options: 21,496

## Package Statistics

### Top 10 Platforms
- x86_64-linux: 118,497 packages
- aarch64-linux: 116,467 packages
- i686-linux: 116,344 packages
- armv7l-linux: 115,540 packages
- armv6l-linux: 115,483 packages
- riscv64-linux: 115,469 packages
- powerpc64le-linux: 115,453 packages
- armv7a-linux: 115,365 packages
- armv5tel-linux: 115,362 packages
- s390x-linux: 115,344 packages`}
                  language="markdown"

                />
              </div>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">Home Manager Resources & Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about Home Manager options and configurations.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">home_manager_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for Home Manager options based on a query string.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Search for options
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_search",
  "params": {
    "query": "programs.neovim",
    "limit": 5
  }
}`}
                language="json"
              />
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a specific Home Manager option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the option</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get option info
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_info",
  "params": {
    "name": "programs.git.enable"
  }
}`}
                language="json"
              />
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_list_options()</AnchorHeading>
            <p className="mb-3 text-gray-800">List all top-level Home Manager option categories with statistics.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: List option categories
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_list_options"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Top-Level Option Categories

Total categories: 25
Total options: 2456

## programs

- **Options count**: 500
- **Option types**:
  - boolean: 149
  - null or package: 39
  - list of string: 32
  - strings concatenated with &quot;\n&quot;: 28
  - package: 23
- **Enable options**: 70
  - abook: Whether to enable Abook..
  - aerc: Whether to enable aerc..
  - aerospace: Whether to enable AeroSpace window manager..
  - ...and 67 more`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_options_by_prefix()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get all Home Manager options under a specific prefix.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">option_prefix</code>: The option prefix to search for (e.g., &quot;programs&quot;, &quot;programs.git&quot;)</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
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
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Options: programs.git

Found 67 options

## Direct Options

- **programs.git.aliases** (aliases) (attribute set of string)
  Git aliases to define.
- **programs.git.attributes** (attributes) (list of string)
  List of defining attributes set globally.
- **programs.git.enable** (enable) (boolean)
  Whether to enable Git.
- **programs.git.extraConfig** (extraConfig) (strings concatenated with "\n" or attribute set of attribute set of (string or boolean or signed integer or list of (string or boolean or signed integer) or attribute set of (string or boolean or signed integer or list of (string or boolean or signed integer))))
  Additional configuration to add. The use of string values is
deprecated and will be removed in the future.
- **programs.git.hooks** (hooks) (attribute set of absolute path)
  Configuration helper for Git hooks.
See https://git-scm.com/docs/githooks
for reference.
- **programs.git.ignores** (ignores) (list of string)
  List of paths that should be globally ignored.

## Option Groups

### cliff options (3)

To see all options in this group, use:
\`home_manager_options_by_prefix(option_prefix="programs.git.cliff")\`

- **enable** (boolean)
- **package** (null or package)
- **settings** (TOML value)

### signing options (4)

To see all options in this group, use:
\`home_manager_options_by_prefix(option_prefix="programs.git.signing")\`

- **format** (null or one of "openpgp", "ssh", "x509")
- **key** (null or string)
- **signByDefault** (null or boolean)
- **signer** (null or string)`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">home_manager_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about Home Manager options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get Home Manager stats
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "home_manager_stats"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Home Manager Option Statistics

Total options: 3704
Categories: 4
Option types: 391

## Distribution by Source

- options: 3697 options
- nix-darwin-options: 7 options

## Top Categories

- Note: 1943 options
- Caution: 1264 options
- Uncategorized: 430 options
- Warning: 74 options

## Distribution by Type

- boolean: 936 options
- null or string: 300 options
- string: 282 options
- package: 239 options
- list of string: 175 options
- strings concatenated with "\n": 145 options
- null or boolean: 137 options
- null or package: 136 options
- null or signed integer: 82 options
- attribute set of string: 71 options

## Index Statistics

- Words indexed: 4382
- Prefix paths: 4432
- Hierarchical parts: 4403`}
                  language="markdown"
                />
              </div>
            </div>
          </section>
          
          <section className="mb-16 bg-nix-light bg-opacity-30 rounded-lg p-6 shadow-sm">
            <AnchorHeading level={3} className="text-xl font-bold mb-4 text-nix-dark">nix-darwin Resources & Tools</AnchorHeading>
            <p className="mb-4 text-gray-800">Tools for searching and retrieving information about nix-darwin macOS options and configurations.</p>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-6 mb-3 text-nix-primary">darwin_search()</AnchorHeading>
            <p className="mb-3 text-gray-800">Search for nix-darwin options based on a query string.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">query</code>: The search term</li>
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">limit</code>: Maximum number of results to return - default: 20</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
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
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`# Search Results for 'keyboard' (5 of 15 results)

## system.keyboard.enableKeyMapping

**Type**: boolean
**Default**: false
**Description**: Whether to enable keyboard mapping.

## system.keyboard.remapCapsLockToControl

**Type**: boolean
**Default**: false
**Description**: Whether to remap the Caps Lock key to Control.

## system.keyboard.remapCapsLockToEscape

**Type**: boolean
**Default**: false
**Description**: Whether to remap the Caps Lock key to Escape.`}
                  language="markdown"

                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_info()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get detailed information about a specific nix-darwin option.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">name</code>: The name of the option</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get option info
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_info",
  "params": {
    "name": "homebrew.enable"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## homebrew.enable
Whether to enable nix-darwin to manage installing/updating/upgrading Homebrew taps, formulae,
and casks, as well as Mac App Store apps and Docker containers, using Homebrew Bundle. Note that enabling this option does not install Homebrew, see the Homebrew website for installation instructions. Use the homebrew.brews , homebrew.casks , homebrew.masApps , and homebrew.whalebrews options
to list the Homebrew formulae, casks, Mac App Store apps, and Docker containers you'd like to
install. Use the homebrew.taps option, to make additional formula
repositories available to Homebrew. This module uses those options (along with the homebrew.caskArgs options) to generate a Brewfile that nix-darwin passes to the brew bundle command during
system activation.

**Type:** boolean
**Default:** false
**Example:** true
**Declared by:** <nix-darwin/modules/homebrew.nix>`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_list_options()</AnchorHeading>
            <p className="mb-3 text-gray-800">List all top-level nix-darwin option categories with statistics.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: List option categories
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_list_options"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin Option Categories
### _module
- **Options count:** 1
- **Usage:** \`darwin._module\`

### documentation
- **Options count:** 4
- **Usage:** \`darwin.documentation\`

### environment
- **Options count:** 34
- **Usage:** \`darwin.environment\`

### fonts
- **Options count:** 1
- **Usage:** \`darwin.fonts\`

### homebrew
- **Options count:** 49
- **Usage:** \`darwin.homebrew\`

### launchd
- **Options count:** 249
- **Usage:** \`darwin.launchd\`

### networking
- **Options count:** 26
- **Usage:** \`darwin.networking\`

### nix
- **Options count:** 55
- **Usage:** \`darwin.nix\`

### nixpkgs
- **Options count:** 10
- **Usage:** \`darwin.nixpkgs\`

### power
- **Options count:** 6
- **Usage:** \`darwin.power\`

### programs
- **Options count:** 69
- **Usage:** \`darwin.programs\`

### security
- **Options count:** 17
- **Usage:** \`darwin.security\`

### services
- **Options count:** 297
- **Usage:** \`darwin.services\`

### system
- **Options count:** 208
- **Usage:** \`darwin.system\`

### time
- **Options count:** 1
- **Usage:** \`darwin.time\`

### users
- **Options count:** 20
- **Usage:** \`darwin.users\`

To view options in a specific category, use the \`darwin_options_by_prefix\` tool with the category name.`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_options_by_prefix()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get all nix-darwin options under a specific prefix.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                <li><code className="font-mono text-nix-dark bg-gray-100 px-1 py-0.5 rounded">option_prefix</code>: The option prefix to search for (e.g., &quot;homebrew&quot;, &quot;system&quot;)</li>
              </ul>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get options by prefix
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_options_by_prefix",
  "params": {
    "option_prefix": "homebrew"
  }
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin options with prefix 'homebrew'
Found 49 options.

### homebrew.brewPrefix
The path prefix where the brew executable is located. This will be set to
the correct value based...
**Type:** \`string\`

For more details, use \`darwin_info("homebrew.brewPrefix")\`

### homebrew.brews
List of Homebrew formulae to install. Formulae defined as strings, e.g., "imagemagick" , are a sh...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.brews")\`

### homebrew.brews._.args
Arguments flags to pass to brew install . Values should not include the
leading "--" . Type: null...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.args")\`

### homebrew.brews._.conflicts_with
List of formulae that should be unlinked and their services stopped (if they are
installed). Type...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.conflicts_with")\`

### homebrew.brews._.link
Whether to link the formula to the Homebrew prefix. When this option is null , Homebrew will use ...
**Type:** \`null\`

For more details, use \`darwin_info("homebrew.brews._.link")\`

### homebrew.brews._.name
The name of the formula to install. Type: string Declared by: <nix-darwin/modules/homebrew.nix>
**Type:** \`string\`

For more details, use \`darwin_info("homebrew.brews._.name")\`

### homebrew.taps
List of Homebrew formula repositories to tap. Taps defined as strings, e.g., "user/repo" , are a ...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.taps")\`

### homebrew.whalebrews
List of Docker images to install using whalebrew . When this option is used, "whalebrew" is autom...
**Type:** \`list\`

For more details, use \`darwin_info("homebrew.whalebrews")\`

[...and more options]`}
                  language="markdown"
                />
              </div>
            </div>
            
            <AnchorHeading level={4} className="text-lg font-semibold mt-8 mb-3 text-nix-primary">darwin_stats()</AnchorHeading>
            <p className="mb-3 text-gray-800">Get statistics about nix-darwin options.</p>
            
            <div className="mb-4 pl-4 border-l-4 border-nix-light">
              <h5 className="font-semibold text-nix-dark mb-2">Parameters:</h5>
              <p className="text-gray-700">This function takes no parameters.</p>
            </div>
            
            <div className="mt-4 mb-6">
              <AnchorHeading level={5} className="text-md font-semibold mb-2 text-nix-primary flex items-center">
                <svg xmlns={"http://www.w3.org/2000/svg"} className="h-5 w-5 mr-2" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d={"M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z"} clipRule="evenodd" />
                </svg>
                Example: Get Darwin stats
              </AnchorHeading>
              <CodeBlock
                code={`{
  "type": "call",
  "tool": "darwin_stats"
}`}
                language="json"
              />
              <div className="mt-2 p-3 bg-gray-50 rounded-md border border-gray-200">
                <h6 className="font-semibold text-nix-dark mb-2">Sample Response:</h6>
                <CodeBlock
                  code={`## nix-darwin Options Statistics
- **Total options:** 1048
- **Total categories:** 16
- **Last updated:** 2025-04-03T22:07:02.122217

### Top-level Categories
- **_module**: 1 options
- **documentation**: 4 options
- **environment**: 34 options
- **fonts**: 1 options
- **homebrew**: 49 options
- **launchd**: 249 options
- **networking**: 26 options
- **nix**: 55 options
- **nixpkgs**: 10 options
- **power**: 6 options
- **programs**: 69 options
- **security**: 17 options
- **services**: 297 options
- **system**: 208 options
- **time**: 1 options
- **users**: 20 options`}
                  language="markdown"
                />
              </div>
            </div>
          </section>
          
          <AnchorHeading level={2} className="text-2xl font-bold mt-12 mb-6 text-nix-primary border-b border-nix-light pb-2">Configuration</AnchorHeading>
          <p className="mb-6 text-gray-800 font-medium">MCP-NixOS can be configured through environment variables:</p>
          
          <div className="overflow-x-auto mb-12 rounded-lg shadow-sm">
            <div className="min-w-full md:min-w-0">
              <table className="w-full border-collapse">
                <thead>
                  <tr className="bg-nix-primary">
                    <th className="px-3 sm:px-6 py-3 text-left text-white font-semibold rounded-tl-lg">Variable</th>
                    <th className="px-3 sm:px-6 py-3 text-left text-white font-semibold rounded-tr-lg">Description</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all">MCP_NIXOS_LOG_LEVEL</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700">Logging level (DEBUG, INFO, WARNING, ERROR)</td>
                  </tr>
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all">MCP_NIXOS_LOG_FILE</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700">Path to log file</td>
                  </tr>
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all">MCP_NIXOS_CACHE_DIR</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700">Directory for cache files</td>
                  </tr>
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all">MCP_NIXOS_CACHE_TTL</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700">Cache time-to-live in seconds</td>
                  </tr>
                  <tr className="hover:bg-nix-light bg-opacity-50 transition-colors duration-150">
                    <td className="px-3 sm:px-6 py-4 font-mono text-xs sm:text-sm font-semibold text-nix-dark break-all rounded-bl-lg">ELASTICSEARCH_URL</td>
                    <td className="px-3 sm:px-6 py-4 text-sm text-gray-700 rounded-br-lg">Custom Elasticsearch URL</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}