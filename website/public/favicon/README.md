# Favicon Files

These favicon files are generated from the MCP-NixOS project logo.

## File Descriptions

- `favicon.ico`: Multi-size ICO file containing 16x14 and 32x28 versions
- `favicon-16x16.png`: 16x14 PNG for standard favicon
- `favicon-32x32.png`: 32x28 PNG for standard favicon
- `apple-touch-icon.png`: 180x156 PNG for iOS home screen
- `android-chrome-192x192.png`: 192x167 PNG for Android
- `android-chrome-512x512.png`: 512x444 PNG for Android
- `safari-pinned-tab.svg`: Monochrome SVG for Safari pinned tabs
- `mstile-150x150.png`: 150x130 PNG for Windows tiles
- `browserconfig.xml`: Configuration for Microsoft browsers
- `site.webmanifest`: Web app manifest for PWA support

## Generation Commands

In a normal development environment, you can generate these files using ImageMagick:

```bash
# Generate PNG files from the source PNG logo
convert -background none -resize 16x16 ../images/mcp-nixos.png favicon-16x16.png
convert -background none -resize 32x32 ../images/mcp-nixos.png favicon-32x32.png
convert -background none -resize 180x180 ../images/mcp-nixos.png apple-touch-icon.png
convert -background none -resize 192x192 ../images/mcp-nixos.png android-chrome-192x192.png
convert -background none -resize 512x512 ../images/mcp-nixos.png android-chrome-512x512.png
convert -background none -resize 150x150 ../images/mcp-nixos.png mstile-150x150.png

# Generate ICO file (combines multiple sizes)
convert favicon-16x16.png favicon-32x32.png favicon.ico
```

## Attribution

These favicon files are derived from the NixOS snowflake logo and are used with attribution to the NixOS project. See the attribution.md file in the images directory for more details.