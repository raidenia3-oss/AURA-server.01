/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/ame',
        destination: '/ame',
      },
      {
        source: '/ame/:path*',
        destination: '/ame/:path*',
      },
      {
        source: '/api/health',
        destination: '/api/health',
      },
    ];
  },
};

module.exports = nextConfig;
