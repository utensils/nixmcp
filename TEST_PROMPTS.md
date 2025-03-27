# NixMCP Test Prompts

This document contains test prompts for manually testing the NixMCP tools with an LLM. These prompts can be used to verify that the tools are working correctly and providing the expected output.

## NixOS Tools

### nixos_search

Test searching for packages:
```
Search for the Firefox package in NixOS.
```

Test searching for options:
```
Search for PostgreSQL configuration options in NixOS.
```

Test searching for programs:
```
Find packages that provide the Python program in NixOS.
```

Test searching with channel specification:
```
Search for the Git package in the stable NixOS channel.
```

Test searching with limit:
```
Show me the top 5 results for "terminal" packages in NixOS.
```

Test searching for service options:
```
What options are available for configuring the nginx service in NixOS?
```

### nixos_info

Test getting package information:
```
Tell me about the Firefox package in NixOS.
```

Test getting option information:
```
What does the services.postgresql.enable option do in NixOS?
```

Test getting information with channel specification:
```
Provide details about the neovim package in the stable NixOS channel.
```

### nixos_stats

Test getting statistics:
```
How many packages and options are available in NixOS?
```

Test getting statistics for a specific channel:
```
Show me statistics for the stable NixOS channel.
```

## Home Manager Tools

### home_manager_search

Test basic search:
```
Search for Git configuration options in Home Manager.
```

Test searching with wildcards:
```
What options are available for Firefox in Home Manager?
```

Test searching with limit:
```
Show me the top 5 Neovim configuration options in Home Manager.
```

Test searching for program options:
```
What options can I configure for the Alacritty terminal in Home Manager?
```

### home_manager_info

Test getting option information:
```
Tell me about the programs.git.enable option in Home Manager.
```

Test getting information for a non-existent option:
```
What does the programs.nonexistent.option do in Home Manager?
```

Test getting information for a complex option:
```
Explain the programs.firefox.profiles option in Home Manager.
```

### home_manager_stats

Test getting statistics:
```
How many configuration options are available in Home Manager?
```

### home_manager_list_options

Test listing top-level options:
```
List all the top-level option categories in Home Manager.
```

### home_manager_options_by_prefix

Test getting options by prefix:
```
Show me all the Git configuration options in Home Manager.
```

Test getting options by category prefix:
```
What options are available under the "programs" category in Home Manager?
```

Test getting options by specific path:
```
List all options under programs.firefox in Home Manager.
```

## nix-darwin Tools

### darwin_search

Test basic search:
```
Search for Dock configuration options in nix-darwin.
```

Test searching with wildcards:
```
What options are available for Homebrew in nix-darwin?
```

Test searching with limit:
```
Show me the top 3 system defaults options in nix-darwin.
```

### darwin_info

Test getting option information:
```
Tell me about the system.defaults.dock.autohide option in nix-darwin.
```

Test getting information for a non-existent option:
```
What does the nonexistent.option do in nix-darwin?
```

### darwin_stats

Test getting statistics:
```
How many configuration options are available in nix-darwin?
```

### darwin_list_options

Test listing top-level options:
```
List all the top-level option categories in nix-darwin.
```

### darwin_options_by_prefix

Test getting options by prefix:
```
Show me all the Dock configuration options in nix-darwin.
```

Test getting options by category prefix:
```
What options are available under the "system" category in nix-darwin?
```

Test getting options by specific path:
```
List all options under system.defaults in nix-darwin.
```

## Combined Testing

Test using multiple tools together:
```
Compare the Git package in NixOS with the Git configuration options in Home Manager.
```

Test searching across all contexts:
```
How can I configure Firefox in NixOS, Home Manager, and nix-darwin?
```

## Edge Cases and Error Handling

Test with invalid input:
```
Search for @#$%^&* in NixOS.
```

Test with empty input:
```
What options are available for "" in Home Manager?
```

Test with very long input:
```
Search for a package with this extremely long name that goes on and on and doesn't actually exist in the repository but I'm typing it anyway to test how the system handles very long input strings that might cause issues with the API or parsing logic...
```

## Performance Testing

Test with high limit:
```
Show me 100 packages that match "lib" in NixOS.
```

Test with complex wildcard patterns:
```
Search for *net*work* options in Home Manager.
```

## Usage Examples

Test with realistic user queries:
```
How do I enable and configure Git with Home Manager?
```

```
I want to customize my macOS Dock using nix-darwin. What options do I have?
```

```
What's the difference between configuring Firefox in NixOS vs Home Manager?
```
