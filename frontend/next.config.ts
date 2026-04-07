import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Permite imagens de domínios externos (ORCID, DiceBear, etc.)
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "info.orcid.org",
      },
      {
        protocol: "https",
        hostname: "api.dicebear.com",
      },
    ],
  },
  // Produção no Render: output standalone para menor tamanho
  output: "standalone",
};

export default nextConfig;
