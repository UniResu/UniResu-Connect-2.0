/**
 * Registro pelo ORCID em uma página só.
 *
 * Quem se registra pelo ORCID preenche o formulário de /registrar antes de
 * ir ao site do ORCID. Os dados ficam guardados neste navegador e, na volta
 * (/callback/orcid), são gravados na conta nova, que já sai com o perfil
 * completo. Se a gravação falhar (e-mail já usado em outra conta, por
 * exemplo), /perfil/completar abre com os mesmos dados e o motivo, para a
 * pessoa corrigir só o que faltou.
 */

const CHAVE = "uniresu_registro_orcid";

/** Tempo para entrar no ORCID (ou criar a conta lá) e voltar. */
const VALIDADE_MS = 2 * 60 * 60 * 1000;

/** Corpo do PATCH /api/perfil que conclui o registro. */
export type DadosRegistro = Record<string, unknown>;

export interface RegistroPendente {
  dados: DadosRegistro;
  guardadoEm: number;
  /** Motivo da falha na volta do ORCID, mostrado em /perfil/completar. */
  erro?: string;
}

export function guardarRegistroPendente(dados: DadosRegistro, erro?: string) {
  try {
    const registro: RegistroPendente = { dados, guardadoEm: Date.now(), erro };
    localStorage.setItem(CHAVE, JSON.stringify(registro));
  } catch {
    // Sem armazenamento (navegação privada restrita): a volta cai em /perfil/completar.
  }
}

export function lerRegistroPendente(): RegistroPendente | null {
  try {
    const bruto = localStorage.getItem(CHAVE);
    if (!bruto) return null;
    const registro = JSON.parse(bruto) as RegistroPendente;
    if (!registro?.dados || !(Date.now() - registro.guardadoEm < VALIDADE_MS)) {
      localStorage.removeItem(CHAVE);
      return null;
    }
    return registro;
  } catch {
    return null;
  }
}

export function descartarRegistroPendente() {
  try {
    localStorage.removeItem(CHAVE);
  } catch {
    // nada guardado
  }
}
