"use client";

import React from 'react';
import CodeBlock from '../../components/CodeBlock';
import AnchorHeading from '@/components/AnchorHeading';

export default function TestCodeBlockPage() {
  const pythonCode = `def hello_world():
    # This is a comment
    print("Hello, world!")
    return 42

# Call the function
result = hello_world()
print(f"The result is {result}")`;

  const nixCode = `{ config, pkgs, lib, ... }:

# This is a NixOS configuration example
{
  imports = [
    ./hardware-configuration.nix
  ];

  # Use the systemd-boot EFI boot loader
  boot.loader.systemd-boot.enable = true;
  boot.loader.efi.canTouchEfiVariables = true;

  # Define a user account
  users.users.alice = {
    isNormalUser = true;
    extraGroups = [ "wheel" "networkmanager" ];
    packages = with pkgs; [
      firefox
      git
      vscode
    ];
  };

  # Enable some services
  services.xserver = {
    enable = true;
    displayManager.gdm.enable = true;
    desktopManager.gnome.enable = true;
  };

  # This value determines the NixOS release
  system.stateVersion = "24.05";
}`;

  const typescriptCode = `import { useState, useEffect } from 'react';

interface User {
  id: number;
  name: string;
  email: string;
}

// This is a React hook that fetches user data
export function useUserData(userId: number): User | null {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  
  useEffect(() => {
    async function fetchData() {
      try {
        const response = await fetch(\`/api/users/\${userId}\`);
        const data = await response.json();
        setUser(data);
      } catch (error) {
        console.error("Failed to fetch user:", error);
      } finally {
        setLoading(false);
      }
    }
    
    fetchData();
  }, [userId]);
  
  return user;
}`;

  return (
    <div className="container mx-auto py-12 px-4">
      <AnchorHeading level={1} className="text-3xl font-bold mb-8 text-nix-primary">Code Block Test Page</AnchorHeading>
      
      <section className="mb-12">
        <AnchorHeading level={2} className="text-2xl font-semibold mb-4 text-nix-dark">Python Example</AnchorHeading>
        <CodeBlock code={pythonCode} language="python" showLineNumbers={true} />
      </section>
      
      <section className="mb-12">
        <AnchorHeading level={2} className="text-2xl font-semibold mb-4 text-nix-dark">Nix Example</AnchorHeading>
        <CodeBlock code={nixCode} language="nix" />
      </section>
      
      <section className="mb-12">
        <AnchorHeading level={2} className="text-2xl font-semibold mb-4 text-nix-dark">TypeScript Example</AnchorHeading>
        <CodeBlock code={typescriptCode} language="typescript" showLineNumbers={true} />
      </section>
    </div>
  );
}
