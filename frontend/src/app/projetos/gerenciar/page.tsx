"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
import Modal from "@/components/ui/Modal";
import styles from "./gerenciar.module.css";

interface Projeto {
  id: string;
  titulo: string;
  descricao: string;
  instituicao?: string;
  tipo?: string;
  local?: string;
  area_estudo?: string;
  modalidade?: string;
  tipo_projeto?: string;
  nome_professor?: string;
  email_professor?: string;
  /** False quando o projeto saiu do ar; os cadastrados aqui nascem ativos. */
  ativo?: boolean;
}

interface FormData {
  titulo: string;
  descricao: string;
  modalidade: string;
  instituicao: string;
  local: string;
  area_estudo: string;
  tipo_projeto: string;
  nome_professor: string;
  email_professor: string;
}

const FORM_VAZIO: FormData = {
  titulo: "",
  descricao: "",
  modalidade: "Presencial",
  instituicao: "",
  local: "",
  area_estudo: "",
  tipo_projeto: "voluntario_aberto",
  nome_professor: "",
  email_professor: "",
};

const AREAS = [
  "Ciências Biológicas e da Saúde",
  "Ciências Exatas e da Terra",
  "Ciências Humanas",
  "Ciências Sociais Aplicadas",
  "Área de Tecnologias",
  "Engenharias",
  "Ciências Agrárias",
  "Artes e Design",
  "Linguística e Letras",
];

/** Rótulo curto do tipo para o chip da lista. */
const TIPO_CHIP: Record<string, string> = {
  voluntario_aberto: "Institucional aberto",
  institucional_exclusivo: "Institucional exclusivo",
};

/* Ícones inline (traço 2, estilo Lucide). */

function IconeMais() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M5 12h14" />
      <path d="M12 5v14" />
    </svg>
  );
}

function IconePasta() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
    </svg>
  );
}

function IconeCadeado() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
      <path d="M7 11V7a5 5 0 0 1 10 0v4" />
    </svg>
  );
}

export default function GerenciarProjetosPage() {
  const { user, token, isLoading: authLoading } = useAuth();
  const router = useRouter();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Formulário
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<FormData>(FORM_VAZIO);
  const [submitting, setSubmitting] = useState(false);

  // Confirmação de exclusão
  const [deleteTarget, setDeleteTarget] = useState<Projeto | null>(null);

  const podeCriar = user?.papel === "professor" || user?.papel === "pesquisador";

  const carregarMeusProjetos = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const data = await api.get<Projeto[]>("/api/projetos/meus", { token });
      setProjetos(data);
    } catch {
      setProjetos([]);
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  const perfilIncompleto = user?.perfil_completo === false;

  useEffect(() => {
    if (!authLoading && !token) {
      router.push("/login"); // Route Guard Master
    } else if (perfilIncompleto) {
      // Conta do ORCID sem vínculo/aceites: a API recusa /projetos/meus (403).
      router.push("/perfil/completar");
    } else if (token && podeCriar) {
      carregarMeusProjetos();
    } else if (!authLoading) {
      setIsLoading(false);
    }
  }, [token, podeCriar, perfilIncompleto, authLoading, carregarMeusProjetos, router]);

  function abrirFormNovo() {
    setForm(FORM_VAZIO);
    setEditingId(null);
    setShowForm(true);
  }

  function abrirFormEditar(projeto: Projeto) {
    setForm({
      titulo: projeto.titulo,
      descricao: projeto.descricao,
      modalidade: projeto.modalidade || "Presencial",
      instituicao: projeto.instituicao || "",
      local: projeto.local || "",
      area_estudo: projeto.area_estudo || "",
      tipo_projeto: projeto.tipo_projeto || "voluntario_aberto",
      nome_professor: projeto.nome_professor || "",
      email_professor: projeto.email_professor || "",
    });
    setEditingId(projeto.id);
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function cancelarForm() {
    setShowForm(false);
    setEditingId(null);
    setForm(FORM_VAZIO);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!token) return;
    setSubmitting(true);

    try {
      if (editingId) {
        await api.put(`/api/projetos/${editingId}`, form, { token });
      } else {
        await api.post("/api/projetos", form, { token });
      }
      cancelarForm();
      await carregarMeusProjetos();
    } catch (err: unknown) {
      const error = err as { detail?: string };
      alert(error.detail || "Erro ao salvar projeto.");
    } finally {
      setSubmitting(false);
    }
  }

  async function confirmarExclusao() {
    if (!deleteTarget || !token) return;
    try {
      await api.delete(`/api/projetos/${deleteTarget.id}`, { token });
      setDeleteTarget(null);
      await carregarMeusProjetos();
    } catch (err: unknown) {
      const error = err as { detail?: string };
      alert(error.detail || "Erro ao excluir projeto.");
    }
  }

  // ── Carregando ou sem permissão ──

  if (authLoading || isLoading) {
    return (
      <div className={styles.pagina}>
        <div className={styles.container}>
          <header className="ui-page-header">
            <h1 className="ui-page-title">Gerenciar projetos</h1>
          </header>
          <div className={`skeleton ${styles.esqueleto}`} />
          <div className={`skeleton ${styles.esqueleto}`} />
        </div>
      </div>
    );
  }

  if (!podeCriar) {
    return (
      <div className={styles.pagina}>
        <div className={styles.container}>
          <div className={`ui-card ${styles.vazio}`} role="status">
            <span className={styles.vazioIcone}>
              <IconeCadeado />
            </span>
            <h1 className={styles.vazioTitulo}>Acesso restrito</h1>
            <p className={styles.vazioTexto}>Apenas docentes e pesquisadores podem gerenciar projetos acadêmicos.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.pagina}>
      <div className={styles.container}>
        <header className={`ui-page-header ${styles.topo}`}>
          <div className={styles.topoTexto}>
            <h1 className="ui-page-title">Gerenciar projetos</h1>
            <p className="ui-page-subtitle">Cadastre e atualize os projetos que você coordena.</p>
          </div>
          {!showForm && (
            <button type="button" className="ui-btn ui-btn-primary" onClick={abrirFormNovo}>
              <IconeMais />
              Novo projeto
            </button>
          )}
        </header>

        {/* ── Formulário ── */}
        {showForm && (
          <form onSubmit={handleSubmit} className={`ui-card ${styles.formulario}`} aria-labelledby="form-titulo">
            <div className={styles.formTopo}>
              <h2 id="form-titulo" className={styles.formTitulo}>
                {editingId ? "Editar projeto" : "Novo projeto"}
              </h2>
              <p className={styles.formDescricao}>
                {editingId
                  ? "As alterações aparecem na busca assim que você salvar."
                  : "O projeto entra na busca pública assim que for salvo."}
              </p>
            </div>

            <div className={styles.grade}>
              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="gp-titulo" className="ui-label">Título</label>
                <input
                  id="gp-titulo"
                  type="text"
                  required
                  className="ui-field"
                  value={form.titulo}
                  onChange={(e) => setForm({ ...form, titulo: e.target.value })}
                />
              </div>

              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="gp-descricao" className="ui-label">Descrição</label>
                <textarea
                  id="gp-descricao"
                  required
                  className="ui-field"
                  rows={5}
                  value={form.descricao}
                  onChange={(e) => setForm({ ...form, descricao: e.target.value })}
                  aria-describedby="gp-descricao-hint"
                />
                <p id="gp-descricao-hint" className="ui-hint">Objetivo, atividades e o perfil de quem você procura.</p>
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-modalidade" className="ui-label">Modalidade</label>
                <select
                  id="gp-modalidade"
                  className="ui-field"
                  value={form.modalidade}
                  onChange={(e) => setForm({ ...form, modalidade: e.target.value })}
                >
                  <option value="Presencial">Presencial</option>
                  <option value="Remoto">Remoto</option>
                  <option value="Híbrido">Híbrido</option>
                </select>
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-instituicao" className="ui-label">Instituição</label>
                <input
                  id="gp-instituicao"
                  type="text"
                  className="ui-field"
                  value={form.instituicao}
                  maxLength={200}
                  placeholder="Ex.: UNIR, UNIRIO"
                  onChange={(e) => setForm({ ...form, instituicao: e.target.value })}
                />
              </div>

              <div className={`${styles.campo} ${styles.inteiro}`}>
                <label htmlFor="gp-local" className="ui-label">Local</label>
                <input
                  id="gp-local"
                  type="text"
                  className="ui-field"
                  value={form.local}
                  placeholder="Ex.: Campus Porto Velho, Laboratório de Bioinformática"
                  onChange={(e) => setForm({ ...form, local: e.target.value })}
                />
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-area" className="ui-label">Área de estudo</label>
                <select
                  id="gp-area"
                  className="ui-field"
                  value={form.area_estudo}
                  onChange={(e) => setForm({ ...form, area_estudo: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {AREAS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-tipo" className="ui-label">Tipo de projeto</label>
                <select
                  id="gp-tipo"
                  className="ui-field"
                  value={form.tipo_projeto}
                  onChange={(e) => setForm({ ...form, tipo_projeto: e.target.value })}
                >
                  <option value="voluntario_aberto">Projeto institucional (aberto)</option>
                  <option value="institucional_exclusivo">Projeto institucional (exclusivo)</option>
                </select>
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-nome" className="ui-label">Nome de quem coordena</label>
                <input
                  id="gp-nome"
                  type="text"
                  className="ui-field"
                  value={form.nome_professor}
                  autoComplete="name"
                  onChange={(e) => setForm({ ...form, nome_professor: e.target.value })}
                />
              </div>

              <div className={styles.campo}>
                <label htmlFor="gp-email" className="ui-label">E-mail de contato</label>
                <input
                  id="gp-email"
                  type="email"
                  className="ui-field"
                  value={form.email_professor}
                  autoComplete="email"
                  onChange={(e) => setForm({ ...form, email_professor: e.target.value })}
                  aria-describedby="gp-email-hint"
                />
                <p id="gp-email-hint" className="ui-hint">Recebe as cartas de intenção enviadas pela plataforma.</p>
              </div>
            </div>

            <div className={styles.rodape}>
              <button type="button" className="ui-btn ui-btn-ghost" onClick={cancelarForm}>
                Cancelar
              </button>
              <button type="submit" className="ui-btn ui-btn-primary" disabled={submitting}>
                {submitting ? "Salvando..." : editingId ? "Salvar alterações" : "Publicar projeto"}
              </button>
            </div>
          </form>
        )}

        {/* ── Lista de projetos ── */}
        {projetos.length === 0 ? (
          <div className={`ui-card ${styles.vazio}`}>
            <span className={styles.vazioIcone}>
              <IconePasta />
            </span>
            <h2 className={styles.vazioTitulo}>Nenhum projeto cadastrado</h2>
            <p className={styles.vazioTexto}>
              Publique o seu primeiro projeto para receber cartas de intenção de discentes interessados.
            </p>
            {!showForm && (
              <button type="button" className={`ui-btn ui-btn-secondary ${styles.vazioAcao}`} onClick={abrirFormNovo}>
                <IconeMais />
                Novo projeto
              </button>
            )}
          </div>
        ) : (
          <ul className={styles.lista} aria-label="Seus projetos">
            {projetos.map((projeto) => (
              <li key={projeto.id} className={`ui-card ${styles.projeto}`}>
                <div className={styles.projetoCorpo}>
                  <div className={styles.projetoChips}>
                    <span className="ui-chip ui-chip-primary">
                      {TIPO_CHIP[projeto.tipo_projeto || ""] || projeto.tipo || "Projeto"}
                    </span>
                    {projeto.ativo === false ? (
                      <span className="ui-chip">Inativo</span>
                    ) : (
                      <span className="ui-chip ui-chip-success">Publicado</span>
                    )}
                    {projeto.modalidade && <span className="ui-chip">{projeto.modalidade}</span>}
                  </div>
                  <h3 className={styles.projetoTitulo}>{projeto.titulo}</h3>
                  <p className={styles.projetoResumo}>{projeto.descricao}</p>
                  {(projeto.instituicao || projeto.area_estudo || projeto.local) && (
                    <div className={styles.projetoMeta}>
                      {projeto.instituicao && <span>{projeto.instituicao}</span>}
                      {projeto.area_estudo && <span>{projeto.area_estudo}</span>}
                      {projeto.local && <span>{projeto.local}</span>}
                    </div>
                  )}
                </div>
                <div className={styles.projetoAcoes}>
                  <button
                    type="button"
                    className="ui-btn ui-btn-sm ui-btn-secondary"
                    onClick={() => abrirFormEditar(projeto)}
                    aria-label={`Editar ${projeto.titulo}`}
                  >
                    Editar
                  </button>
                  <button
                    type="button"
                    className="ui-btn ui-btn-sm ui-btn-danger"
                    onClick={() => setDeleteTarget(projeto)}
                    aria-label={`Excluir ${projeto.titulo}`}
                  >
                    Excluir
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}

        {/* ── Confirmação de exclusão ── */}
        {deleteTarget && (
          <Modal aberto titulo="Excluir projeto?" onFechar={() => setDeleteTarget(null)} botaoRodape={false}>
            <p className={styles.modalTexto}>
              Tem certeza que deseja excluir &quot;{deleteTarget.titulo}&quot;? Esta ação não pode ser desfeita.
            </p>
            <div className={styles.modalAcoes}>
              <button type="button" className="ui-btn ui-btn-ghost" onClick={() => setDeleteTarget(null)}>
                Cancelar
              </button>
              <button type="button" className="ui-btn ui-btn-danger" onClick={confirmarExclusao}>
                Excluir
              </button>
            </div>
          </Modal>
        )}
      </div>
    </div>
  );
}
