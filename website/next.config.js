/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Enable static exports for S3/CloudFront
  distDir: 'out',    // Output directory for static export
  images: {
    unoptimized: true, // Required for static export
  },
  reactStrictMode: true,
};

module.exports = nextConfig;