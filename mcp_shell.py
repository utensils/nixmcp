#!/usr/bin/env python
"""
MCP-NixOS Interactive Shell

A minimalist interactive shell for exploring and manually interacting with the MCP-NixOS server.
This version uses a hardcoded list of known tools and simply logs all server output.

Usage:
  python mcp_shell.py

Commands:
  help                   - Show available commands
  tools                  - Show available tools
  call <tool> [params]   - Call a tool with optional JSON parameters
  exit/quit              - Exit the shell
"""

import json
import os
import sys
import subprocess
import signal
import threading
import time
from typing import Dict, Any, List

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "cyan": "\033[36m",
    "bold": "\033[1m"
}

# Default tools to use if discovery fails
DEFAULT_TOOLS = [
    "nixos_search", "nixos_info", "nixos_stats",
    "home_manager_search", "home_manager_info", "home_manager_stats",
    "darwin_search", "darwin_info", "darwin_stats", "darwin_list_options", "darwin_options_by_prefix",
    "mcp__nixos__nixos_search", "mcp__nixos__nixos_info", "mcp__nixos__nixos_stats",
    "mcp__nixos__home_manager_search", "mcp__nixos__home_manager_info", "mcp__nixos__home_manager_stats",
    "mcp__nixos__darwin_search", "mcp__nixos__darwin_info", "mcp__nixos__darwin_stats",
    "mcp__nixos__darwin_list_options", "mcp__nixos__darwin_options_by_prefix"
]

# Will be populated during initialization
AVAILABLE_TOOLS = []

# Global variables
server_process = None
stop_threads = False

# Print functions
def print_header(text): print(f"\n{COLORS['bold']}{COLORS['blue']}=== {text} ==={COLORS['reset']}\n")
def print_error(text): print(f"{COLORS['red']}ERROR: {text}{COLORS['reset']}")
def print_warning(text): print(f"{COLORS['yellow']}WARNING: {text}{COLORS['reset']}")
def print_success(text): print(f"{COLORS['green']}{text}{COLORS['reset']}")
def print_info(text): print(f"{COLORS['cyan']}{text}{COLORS['reset']}")
def print_json(data): print(json.dumps(data, indent=2))

def show_help():
    """Show available commands."""
    print_header("Available Commands")
    print("  help                   - Show this help message")
    print("  tools                  - Show available tools")
    print("  call <tool> [params]   - Call a tool with optional JSON parameters")
    print("  exit/quit              - Exit the shell")

def read_output(stream, prefix):
    """Read from stdout/stderr and print it."""
    global stop_threads, AVAILABLE_TOOLS
    output_buffer = ""
    
    try:
        for line in iter(stream.readline, ""):
            if stop_threads:
                break
                
            # Skip empty lines
            if not line.strip():
                continue
                
            # Log line with appropriate color
            if "ERROR" in line:
                print_error(f"{prefix}: {line.strip()}")
            elif "WARNING" in line:
                print_warning(f"{prefix}: {line.strip()}")
            else:
                print_info(f"{prefix}: {line.strip()}")
                
            # For stdout, try to collect JSON responses
            if prefix == "STDOUT":
                # Add line to buffer
                output_buffer += line
                
                # Try to parse as JSON
                try:
                    data = json.loads(output_buffer)
                    output_buffer = ""  # Reset buffer on successful parse
                    
                    # Check if it's a tools list response
                    if "tools" in data and isinstance(data["tools"], list):
                        AVAILABLE_TOOLS = data["tools"]
                        print_success(f"Discovered {len(AVAILABLE_TOOLS)} tools")
                    elif "result" in data:
                        if isinstance(data["result"], dict):
                            # Print the tool result
                            print_header("Tool Result")
                            print_json(data["result"])
                        elif isinstance(data["result"], list):
                            # Print list result
                            print_header("Tool Result")
                            print_json(data["result"])
                        else:
                            # Print simple result
                            print_header("Tool Result")
                            print(data["result"])
                except json.JSONDecodeError:
                    # If it doesn't parse as JSON, check if it might be the end of a block
                    if line.strip() in ["}", "]"]:
                        try:
                            data = json.loads(output_buffer)
                            output_buffer = ""
                            # Process same as above
                            if "tools" in data and isinstance(data["tools"], list):
                                AVAILABLE_TOOLS = data["tools"]
                                print_success(f"Discovered {len(AVAILABLE_TOOLS)} tools")
                        except:
                            pass  # Not a complete JSON object
    except Exception as e:
        if not stop_threads:
            print_error(f"Error reading from {prefix}: {e}")

def start_server():
    """Start the MCP server process."""
    global server_process
    try:
        print_info("Starting MCP-NixOS server...")
        
        # Environment setup
        env = os.environ.copy()
        env["MCP_NIXOS_LOG_LEVEL"] = "INFO"  # Use INFO instead of DEBUG to reduce noise
        
        # Start the server process
        server_process = subprocess.Popen(
            ["uv", "run", "-m", "mcp_nixos"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=env
        )
        print_success("Server process started")
        
        # Setup threads to read output
        stdout_thread = threading.Thread(
            target=read_output,
            args=(server_process.stdout, "STDOUT"),
            daemon=True
        )
        stderr_thread = threading.Thread(
            target=read_output,
            args=(server_process.stderr, "SERVER"),
            daemon=True
        )
        
        stdout_thread.start()
        stderr_thread.start()
        
        return True
    except Exception as e:
        print_error(f"Failed to start server: {e}")
        return False

def stop_server():
    """Stop the server process."""
    global server_process, stop_threads
    
    if server_process:
        print_info("Stopping server process...")
        stop_threads = True
        try:
            server_process.terminate()
            try:
                server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print_warning("Server did not terminate gracefully, forcing kill")
                server_process.kill()
        except Exception as e:
            print_error(f"Error stopping server: {e}")

def send_command(process, command):
    """Send a command to the server process."""
    if not process or process.poll() is not None:
        print_error("Server process is not running")
        return False
        
    if not process.stdin:
        print_error("Cannot access server stdin")
        return False
        
    try:
        # Generate a message ID if not present
        if isinstance(command, dict) and "id" not in command:
            import uuid
            command["id"] = str(uuid.uuid4())
            
        # Convert to JSON string with newline
        message = json.dumps(command) + "\n"
        
        # Log the message
        print_info(f"Sending: {message.strip()}")
        
        # Send the command
        process.stdin.write(message)
        process.stdin.flush()
        return True
    except Exception as e:
        print_error(f"Error sending command: {e}")
        return False

def discover_tools():
    """Attempt to discover available tools from the server."""
    global AVAILABLE_TOOLS, server_process
    
    print_info("Attempting to discover available tools...")
    
    # Try different message formats to discover tools
    tool_discovery_formats = [
        {"type": "list_tools"},
        {"jsonrpc": "2.0", "method": "list_tools", "params": {}},
        {"command": "list_tools"}
    ]
    
    # Send all formats to try to get a response
    for msg_format in tool_discovery_formats:
        print_info(f"Trying tool discovery format: {json.dumps(msg_format)}")
        send_command(server_process, msg_format)
        time.sleep(0.5)  # Brief delay between messages
    
    # Wait a bit for any responses
    print_info("Waiting for tool discovery response...")
    time.sleep(2)
    
    # If no tools discovered, use defaults
    if not AVAILABLE_TOOLS:
        print_warning("Could not discover tools dynamically, using default list")
        AVAILABLE_TOOLS.extend(DEFAULT_TOOLS)
        
    print_success(f"Using {len(AVAILABLE_TOOLS)} tools")

def main():
    """Main function."""
    global AVAILABLE_TOOLS
    
    # Initial setup
    print_header("MCP-NixOS Interactive Shell")
    print_info("Type 'help' for available commands")
    
    # Start the server
    if not start_server():
        return 1
        
    # Set up signal handlers for graceful exit
    signal.signal(signal.SIGINT, lambda sig, frame: None)
    signal.signal(signal.SIGTERM, lambda sig, frame: stop_server())
    
    try:
        # Wait for server initialization
        print_info("Waiting for server to initialize...")
        time.sleep(3)
        
        # Try to discover available tools
        discover_tools()
        
        # Command loop
        while True:
            try:
                cmd = input(f"{COLORS['bold']}> {COLORS['reset']}")
                cmd = cmd.strip()
                
                if not cmd:
                    continue
                    
                if cmd in ["exit", "quit"]:
                    break
                    
                elif cmd == "help":
                    show_help()
                    
                elif cmd == "tools":
                    print_header("Available Tools")
                    for tool in sorted(AVAILABLE_TOOLS):
                        print(f"  {tool}")
                    
                elif cmd.startswith("call "):
                    # Parse the command
                    parts = cmd.split(" ", 2)
                    if len(parts) < 2:
                        print_error("Invalid command format. Usage: call <tool> [params]")
                        continue
                        
                    tool_name = parts[1]
                    params_str = parts[2] if len(parts) > 2 else "{}"
                    
                    # Warn but don't block if tool not in known list
                    if tool_name not in AVAILABLE_TOOLS:
                        print_warning(f"Warning: Tool '{tool_name}' not in discovered tool list")
                        print_info("Attempting to call it anyway")
                        
                    # Parse parameters
                    try:
                        params = json.loads(params_str)
                    except json.JSONDecodeError:
                        print_error(f"Invalid JSON: {params_str}")
                        continue
                        
                    # Call the tool
                    print_info(f"Calling tool: {tool_name}")
                    print_info("Parameters:")
                    print_json(params)
                    
                    # Format command based on tool name
                    if tool_name.startswith("mcp__"):
                        command = {
                            "jsonrpc": "2.0",
                            "method": tool_name,
                            "params": params
                        }
                    else:
                        command = {
                            "type": "call",
                            "tool": tool_name,
                            "params": params
                        }
                        
                    # Send the command
                    send_command(server_process, command)
                    
                else:
                    print_error(f"Unknown command: {cmd}")
                    print_info("Type 'help' for available commands")
                    
            except KeyboardInterrupt:
                print("\nUse 'exit' or 'quit' to exit the shell")
            except EOFError:
                print_error("Input stream closed")
                break
            except Exception as e:
                print_error(f"Error: {e}")
                
    finally:
        # Clean up
        stop_server()
        print_success("Shell terminated successfully")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())