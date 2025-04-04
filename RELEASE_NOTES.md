# MCP-NixOS: v0.3.1 Release Notes

## Overview

MCP-NixOS v0.3.1 is a patch release that fixes critical issues with the Home Manager and NixOS tools when used through Claude's Model Context Protocol (MCP) interface.

## Changes in v0.3.1

### 🐛 Bug Fixes

- **Fixed Home Manager context handling in MCP interface**: Resolved issues where Home Manager tools would fail with `'str' object has no attribute 'request_context'` error when accessed through Claude's MCP interface
- **Improved context type validation**: Added proper type checking with `isinstance(ctx, str)` to handle both server request contexts and string contexts from MCP
- **Enhanced error handling in tool registration**: Modified MCP tool registration to dynamically import the proper context when string contexts are passed
- **Restored dependency lock file**: Added `uv.lock` to ensure consistent dependencies across all environments, fixing missing `psutil` dependency issues

## Technical Details

The fundamental issue occurred in the context handling within the MCP-NixOS integration:

1. **Inconsistent Context Types**: The Home Manager tools were originally designed to handle `request_context` objects from the internal server, but when called through Claude's MCP interface, they received a string context instead.

2. **Type Mismatch Error**: This led to the error `'str' object has no attribute 'request_context'` when the tools tried to access `ctx.request_context` on a string.

3. **Two-Layer Context Problem**: The issue existed in both:
   - The direct tool functions 
   - The MCP tool registration wrappers

The fix required implementing proper type checking in both the tool functions themselves and in their MCP registration wrappers, along with appropriate handling for string contexts by dynamically importing the proper context object.

## Installation

```bash
# Install with pip
pip install mcp-nixos==0.3.1

# Install with uv
uv pip install mcp-nixos==0.3.1

# Install with uvx
uvx mcp-nixos==0.3.1
```

## Usage

Configure Claude to use the tool by adding it to your `~/.config/claude/config.json` file:

```json
{
  "tools": [
    {
      "path": "mcp_nixos",
      "default_enabled": true
    }
  ]
}
```

## Contributors

- James Brink (@utensils)
- Sean Callan (Moral Support)