# MCP-NixOS Website

The official website for the MCP-NixOS project built with Next.js 15.2 and Tailwind CSS.

## Development

This website is built with:

- [Next.js 15.2](https://nextjs.org/) using the App Router
- [TypeScript](https://www.typescriptlang.org/)
- [Tailwind CSS](https://tailwindcss.com/) for styling
- Static export for hosting on S3/CloudFront

## Getting Started

### Using Nix (Recommended)

If you have Nix installed, you can use the dedicated website development shell:

#### Option 1: Direct Website Shell Access
```bash
# Enter the website development shell directly
nix develop .#web

# Use the menu commands or run directly:
install   # Install dependencies 
dev       # Start development server
build     # Build for production
lint      # Lint code
```

#### Option 2: From Main Development Shell
```bash
# Enter the main development shell
nix develop

# Launch the website development shell
web-dev   # This opens the website shell with Node.js
```

### Manual Setup

```bash
# Navigate to the website directory
cd website

# Install dependencies
npm install
# or
yarn
# or
pnpm install

# Start development server
npm run dev
# or
yarn dev
# or
pnpm dev

# Build for production
npm run build
# or
yarn build
# or
pnpm build
```

## Project Structure

- `app/` - Next.js app router pages
- `components/` - Shared UI components
- `public/` - Static assets
- `tailwind.config.js` - Tailwind CSS configuration with NixOS color scheme

## Design Notes

- The website follows NixOS brand colors:
  - Primary: #5277C3
  - Secondary: #7EBAE4
  - Dark Blue: #1C3E5A
  - Light Blue: #E6F0FA

- Designed to be fully responsive for mobile, tablet, and desktop
- SEO optimized with proper metadata
- Follows accessibility guidelines (WCAG 2.1 AA)