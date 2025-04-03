import type { Metadata, Viewport } from 'next';
import './globals.css';
import Navbar from '@/components/Navbar';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'MCP-NixOS | Model Context Protocol for NixOS',
  description: 'MCP resources and tools for NixOS packages, system options, Home Manager configuration, and nix-darwin macOS configuration.',
  keywords: ['NixOS', 'MCP', 'Model Context Protocol', 'Home Manager', 'nix-darwin', 'Claude', 'AI Assistant'],
  icons: {
    icon: [
      { url: '/favicon/favicon.ico' },
      { url: '/favicon/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/favicon/favicon-32x32.png', sizes: '32x32', type: 'image/png' }
    ],
    apple: [
      { url: '/favicon/apple-touch-icon.png' }
    ],
    other: [
      {
        rel: 'mask-icon',
        url: '/favicon/safari-pinned-tab.svg',
        color: '#5277c3'
      }
    ]
  },
  manifest: '/favicon/site.webmanifest',
};

export const viewport: Viewport = {
  themeColor: '#5277c3',
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