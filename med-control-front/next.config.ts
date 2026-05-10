import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [new URL('https://lh3.googleusercontent.com/**')]
  },
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.API_INTERNAL_URL ?? 'http://localhost:8000'}/:path*`,
      },
    ]
  },
};

export default nextConfig;
