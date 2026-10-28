import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: process.env.RETURNET_STANDALONE === "true" ? "standalone" : undefined,
  reactStrictMode: true,
  poweredByHeader: false,
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(), geolocation=(), microphone=()" }
      ]
    }];
  }
};

export default nextConfig;
