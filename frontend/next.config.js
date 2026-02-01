/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    // In development, proxy API calls to local backend
    // In production, use the API routes
    return process.env.NODE_ENV === 'development' ? [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ] : [];
  },
};

module.exports = nextConfig;
