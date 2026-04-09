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
      detail = errorData.detail || detail;
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
