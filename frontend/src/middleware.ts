/**
 * Next.js Middleware — proteção de rotas.
 *
 * Nota: Middleware roda no Edge, sem acesso a localStorage.
 * A proteção real é feita pelo AuthContext no client-side.
 * Este middleware serve como camada adicional usando cookies
 * (quando implementado) ou apenas para redirecionamentos básicos.
 */

import { NextRequest, NextResponse } from "next/server";

const PROTECTED_ROUTES = ["/perfil", "/projetos/novo"];
const AUTH_ROUTES = ["/login", "/registrar"];

export function middleware(request: NextRequest) {
  // Por enquanto, a autenticação é gerenciada client-side via AuthContext.
  // Quando os tokens forem salvos em httpOnly cookies (fase 3),
  // este middleware poderá validar cookies diretamente.
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/perfil/:path*",
    "/projetos/novo",
    "/login",
    "/registrar",
  ],
};
