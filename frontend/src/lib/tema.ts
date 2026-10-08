/**
 * Tema claro/escuro.
 *
 * O tema vive no atributo `data-theme` do <html> (lido pelo globals.css). A
 * escolha da pessoa fica no localStorage; sem escolha, vale a preferência do
 * sistema. O script inline em layout.tsx aplica o atributo antes da primeira
 * pintura, para a página não piscar em claro antes de ficar escura.
 */

export type Tema = "light" | "dark";

export const CHAVE_TEMA = "uniresu-tema";

/** Código do script inline (sem dependências, roda antes do React). */
export const SCRIPT_TEMA = `(function(){try{var t=localStorage.getItem(${JSON.stringify(CHAVE_TEMA)});if(t!=="light"&&t!=="dark"){t=window.matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}document.documentElement.setAttribute("data-theme",t)}catch(e){document.documentElement.setAttribute("data-theme","light")}})();`;

export function temaDoSistema(): Tema {
  if (typeof window === "undefined") return "light";
  return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

export function temaSalvo(): Tema | null {
  try {
    const t = localStorage.getItem(CHAVE_TEMA);
    return t === "light" || t === "dark" ? t : null;
  } catch {
    return null;
  }
}

export function temaAtual(): Tema {
  if (typeof document === "undefined") return "light";
  const t = document.documentElement.getAttribute("data-theme");
  return t === "dark" ? "dark" : "light";
}

export function aplicarTema(tema: Tema, salvar = true) {
  document.documentElement.setAttribute("data-theme", tema);
  if (salvar) {
    try {
      localStorage.setItem(CHAVE_TEMA, tema);
    } catch {
      /* armazenamento indisponível (modo privado): o tema vale só nesta visita */
    }
  }
}
