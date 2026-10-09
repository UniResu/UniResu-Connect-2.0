import type { MetadataRoute } from "next";
import { SITE_URL } from "@/lib/constants";

/** robots.txt: tudo aberto, menos as telas de conta, e o endereço do sitemap. */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/perfil",
        "/candidaturas",
        "/projetos/gerenciar",
        "/callback",
        "/verificar-email",
        "/recuperar-senha",
        "/resetar-senha",
      ],
    },
    sitemap: `${SITE_URL}/sitemap.xml`,
  };
}
