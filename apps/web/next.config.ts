import type { NextConfig } from "next";

const localApiOrigin = process.env.LOCAL_API_ORIGIN ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  async rewrites() {
    if (process.env.NODE_ENV === "development") {
      return [
        {
          source: "/sessions",
          destination: `${localApiOrigin}/sessions`,
        },
        {
          source: "/sessions/:path*",
          destination: `${localApiOrigin}/sessions/:path*`,
        },
        {
          source: "/rfq-templates/:path*",
          destination: `${localApiOrigin}/rfq-templates/:path*`,
        },
        {
          source: "/healthz",
          destination: `${localApiOrigin}/healthz`,
        },
      ];
    }

    return [
      {
        source: "/sessions",
        destination: "/api/sessions",
      },
      {
        source: "/sessions/:path*",
        destination: "/api/sessions/:path*",
      },
      {
        source: "/rfq-templates/:path*",
        destination: "/api/rfq-templates/:path*",
      },
      {
        source: "/healthz",
        destination: "/api/healthz",
      },
    ];
  },
};

export default nextConfig;
