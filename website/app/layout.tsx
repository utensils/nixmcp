import type { Metadata } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'MCP-NixOS | Model Context Protocol for NixOS',
  description: 'MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration.',
  keywords: ['NixOS', 'MCP', 'Model Context Protocol', 'Home Manager', 'nix-darwin', 'Claude', 'AI Assistant'],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-grow">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}