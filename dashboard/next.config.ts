import type { NextConfig } from "next";

const ANALYTICS_API = process.env.NEXT_PUBLIC_ANALYTICS_API_URL;
const DATA_API = process.env.NEXT_PUBLIC_DATA_API_URL;

const nextConfig: NextConfig = {
  assetPrefix: '',
  basePath: '',
  trailingSlash: false,
  async rewrites() {
    const rewrites = [];
    
    // Analytics service proxy
    if (ANALYTICS_API) {
      rewrites.push({
        source: '/api/analytics/:path*',
        destination: `${ANALYTICS_API}/:path*`,
      });
    }
    
    // Data service proxy  
    if (DATA_API) {
      rewrites.push({
        source: '/api/data/:path*',
        destination: `${DATA_API}/:path*`,
      });
    }
    
    return rewrites;
  },
};

export default nextConfig;
