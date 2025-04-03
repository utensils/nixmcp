/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Enable static exports for S3/CloudFront
  distDir: 'out',    // Output directory for static export
  images: {
    unoptimized: true, // Required for static export
  },
  reactStrictMode: true,
  
  // Allow cross-origin requests during development (for VS Code browser preview)
  allowedDevOrigins: [
    '127.0.0.1',
  ],
};

module.exports = nextConfig;