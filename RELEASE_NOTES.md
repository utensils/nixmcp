# MCP-NixOS: v0.4.0 Release Notes

## Overview

MCP-NixOS v0.4.0 introduces significant architectural improvements, focusing on resolving critical issues with channel switching and context management. This release also includes a completely redesigned prompt system following Model Context Protocol (MCP) best practices for dynamic discovery.

## Changes in v0.4.0

### 🚀 Major Enhancements

- **Fixed Channel Switching Functionality**: Resolved issues with channel switching between stable and unstable NixOS versions, ensuring accurate data retrieval for different channels
- **Improved Context Management**: Completely refactored context management to eliminate type confusion and provide consistent handling across all tools
- **Dynamic Discovery Tools**: Implemented discovery tools following MCP best practices, enabling AI to explore available capabilities dynamically
- **Redesigned MCP Prompt**: Replaced the extensive documentation with a concise, principle-based prompt that emphasizes proper tool usage patterns

### 🛠️ Implementation Details

- **Channel Validation**: Added proper validation to ensure channel switching actually retrieves distinct data
- **Context Type Consistency**: Standardized context handling across NixOS, Home Manager, and Darwin tools
- **Enhanced Parameter Documentation**: Improved documentation for the `ctx` parameter across all tools
- **Comprehensive Testing**: Added new tests for channel switching and context handling

## Technical Details

The release addresses two main architectural issues:

1. **Channel Switching Failure**: Previously, switching between channels (like "unstable" and "24.11") didn't properly change the Elasticsearch index, resulting in identical data regardless of channel selection. This has been fixed with proper verification of channel differences.

2. **Context Management Chaos**: The codebase had inconsistent handling of the `ctx` parameter across different tools, sometimes treating it as a request context object and other times as a string identifier. This has been standardized with proper type checking and appropriate handling for all context types.

3. **Dynamic Discovery**: Following MCP best practices, tools now support dynamic discovery rather than requiring hardcoded documentation in the prompt, making the system more maintainable and scalable.

## Installation

```bash
# Install with pip
pip install mcp-nixos==0.4.0

# Install with uv
uv pip install mcp-nixos==0.4.0

# Install with uvx
uvx mcp-nixos==0.4.0
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