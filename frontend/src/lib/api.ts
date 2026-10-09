/**
 * Cliente HTTP para a API FastAPI.
 *
 * Wrapper sobre fetch que:
 * - Adiciona baseURL da API
 * - Injeta Authorization header quando há token
 * - Trata erros de forma consistente
 */

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://api.uniresu.org";

interface ApiOptions extends RequestInit {
  token?: string;
}

interface ApiError {
  status: number;
  detail: string;
}

/**
 * `detail` do FastAPI é uma string nos erros de negócio e uma lista de
 * objetos `{loc, msg, ...}` nos erros de validação (422). Sempre devolvemos
 * uma string: renderizar a lista direto no JSX derruba a página.
 */
function normalizarDetail(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const msg = typeof d === "string" ? d : (d as { msg?: string })?.msg || "";
        return msg.replace(/^Value error, /, "");
      })
      .filter(Boolean)
      .join(" ");
  }
  if (detail && typeof detail === "object" && "msg" in (detail as object)) {
    return String((detail as { msg?: string }).msg || "");
  }
  return "";
}

async function request<T>(
  endpoint: string,
  options: ApiOptions = {}
): Promise<T> {
  const { token, headers: customHeaders, ...fetchOptions } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...customHeaders,
  };

  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (!res.ok) {
    let detail = "Erro desconhecido";
    try {
      const errorData = await res.json();
      detail = normalizarDetail(errorData.detail) || detail;
    } catch {
      detail = res.statusText;
    }
    const error: ApiError = { status: res.status, detail };
    throw error;
  }

  // 204 No Content (ex.: DELETE) não tem body — chamar res.json() lançaria
  // SyntaxError. Também cobrimos Content-Length: 0 por precaução.
  if (res.status === 204 || res.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return res.json();
}

/**
 * Pede /health sem esperar resposta. No plano gratuito do Render a API dorme
 * depois de 15 minutos parada e leva perto de um minuto para acordar; chamar
 * isto cedo faz a espera acontecer enquanto a pessoa ainda lê a página.
 * `no-cors` porque só importa a requisição chegar, não a resposta.
 */
export function acordarApi() {
  fetch(`${API_URL}/health`, { mode: "no-cors", cache: "no-store" }).catch(() => {});
}

export const api = {
  get: <T>(endpoint: string, options?: ApiOptions) =>
    request<T>(endpoint, { ...options, method: "GET" }),

  post: <T>(endpoint: string, body: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "POST",
      body: JSON.stringify(body),
    }),

  patch: <T>(endpoint: string, body: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "PATCH",
      body: JSON.stringify(body),
    }),

  put: <T>(endpoint: string, body: unknown, options?: ApiOptions) =>
    request<T>(endpoint, {
      ...options,
      method: "PUT",
      body: JSON.stringify(body),
    }),

  delete: <T>(endpoint: string, options?: ApiOptions) =>
    request<T>(endpoint, { ...options, method: "DELETE" }),
};
