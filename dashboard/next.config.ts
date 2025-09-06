import type { NextConfig } from "next";

const ANALYTICS_API = process.env.NEXT_PUBLIC_ANALYTICS_API_URL || "";

const nextConfig: NextConfig = {
  assetPrefix: '',
  basePath: '',
  trailingSlash: false,
  async rewrites() {
    if (!ANALYTICS_API) return [];
    return [
      {
        source: '/api/analytics/:path*',
        destination: `${ANALYTICS_API}/:path*`,
      },
    ];
  },
};

export default nextConfig;
