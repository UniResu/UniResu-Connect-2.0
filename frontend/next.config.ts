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
  // Links antigos de projeto (/projetos?projeto=<id>, o endereço do modal)
  // levam à página própria do projeto, que tem título e prévia de link.
  // Dentro da busca o modal continua igual: a troca do endereço lá é feita
  // pelo navegador, sem passar pelo servidor.
  async redirects() {
    return [
      {
        source: "/projetos",
        has: [{ type: "query", key: "projeto", value: "(?<id>[a-f0-9]{24})" }],
        destination: "/projetos/:id",
        permanent: true,
      },
    ];
  },
};

export default nextConfig;
