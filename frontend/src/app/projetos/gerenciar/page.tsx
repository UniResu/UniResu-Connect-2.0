"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/lib/api";
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

export default function GerenciarProjetosPage() {
  const { user, token, isLoading: authLoading } = useAuth();
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

  useEffect(() => {
    if (token && podeCriar) {
      carregarMeusProjetos();
    } else if (!authLoading) {
      setIsLoading(false);
    }
  }, [token, podeCriar, authLoading, carregarMeusProjetos]);

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

  // ── Loading ou sem permissão ──

  if (authLoading || isLoading) {
    return (
      <div className={styles.page}>
        <div className={styles.loadingState}>Carregando...</div>
      </div>
    );
  }

  if (!podeCriar) {
    return (
      <div className={styles.page}>
        <div className={styles.accessDenied}>
          <h2>🔒 Acesso Restrito</h2>
          <p>Apenas professores e pesquisadores podem gerenciar projetos acadêmicos.</p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>Gerenciar Projetos</h1>

      {/* ── Botão Novo ── */}
      {!showForm && (
        <button className={styles.btnNovo} onClick={abrirFormNovo}>
          + Novo Projeto
        </button>
      )}

      {/* ── Formulário ── */}
      {showForm && (
        <div className={styles.formCard}>
          <h2 className={styles.formTitle}>
            {editingId ? "Editar Projeto" : "Novo Projeto"}
          </h2>
          <form onSubmit={handleSubmit} className={styles.formGrid}>
            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Título</label>
              <input
                type="text"
                required
                className={styles.formInput}
                value={form.titulo}
                onChange={(e) => setForm({ ...form, titulo: e.target.value })}
              />
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Descrição</label>
              <textarea
                required
                className={styles.formTextarea}
                value={form.descricao}
                onChange={(e) => setForm({ ...form, descricao: e.target.value })}
              />
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Modalidade</label>
                <select
                  className={styles.formSelect}
                  value={form.modalidade}
                  onChange={(e) => setForm({ ...form, modalidade: e.target.value })}
                >
                  <option value="Presencial">Presencial</option>
                  <option value="Remoto">Remoto</option>
                  <option value="Híbrido">Híbrido</option>
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Instituição</label>
                <input
                  type="text"
                  className={styles.formInput}
                  value={form.instituicao}
                  onChange={(e) => setForm({ ...form, instituicao: e.target.value })}
                />
              </div>
            </div>

            <div className={styles.formGroup}>
              <label className={styles.formLabel}>Local</label>
              <input
                type="text"
                className={styles.formInput}
                value={form.local}
                onChange={(e) => setForm({ ...form, local: e.target.value })}
              />
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Área de Estudo</label>
                <select
                  className={styles.formSelect}
                  value={form.area_estudo}
                  onChange={(e) => setForm({ ...form, area_estudo: e.target.value })}
                >
                  <option value="">Selecione</option>
                  {AREAS.map((a) => (
                    <option key={a} value={a}>{a}</option>
                  ))}
                </select>
              </div>

              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Tipo de Projeto</label>
                <select
                  className={styles.formSelect}
                  value={form.tipo_projeto}
                  onChange={(e) => setForm({ ...form, tipo_projeto: e.target.value })}
                >
                  <option value="voluntario_aberto">Projeto Institucional (Aberto)</option>
                  <option value="institucional_exclusivo">Projeto Institucional (Exclusivo)</option>
                </select>
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.formGroup}>
                <label className={styles.formLabel}>Nome do Professor/Pesquisador</label>
                <input
                  type="text"
                  className={styles.formInput}
                  value={form.nome_professor}
                  onChange={(e) => setForm({ ...form, nome_professor: e.target.value })}
                />
              </div>

              <div className={styles.formGroup}>
                <label className={styles.formLabel}>E-mail do Professor/Pesquisador</label>
                <input
                  type="email"
                  className={styles.formInput}
                  value={form.email_professor}
                  onChange={(e) => setForm({ ...form, email_professor: e.target.value })}
                />
              </div>
            </div>

            <div className={styles.formActions}>
              <button
                type="submit"
                className={styles.btnSalvar}
                disabled={submitting}
              >
                {submitting ? "Salvando..." : "Salvar"}
              </button>
              <button
                type="button"
                className={styles.btnCancelar}
                onClick={cancelarForm}
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* ── Lista de Projetos ── */}
      {projetos.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>📋</span>
          <h3>Nenhum projeto cadastrado</h3>
          <p>Clique em &quot;+ Novo Projeto&quot; para publicar seu primeiro projeto.</p>
        </div>
      ) : (
        <div className={styles.projetosList}>
          {projetos.map((projeto) => (
            <div key={projeto.id} className={styles.projetoCard}>
              <div className={styles.projetoHeader}>
                <div className={styles.projetoInfo}>
                  <h3 className={styles.projetoTitulo}>{projeto.titulo}</h3>
                  <p className={styles.projetoDesc}>{projeto.descricao}</p>
                  <div className={styles.projetoMeta}>
                    {projeto.instituicao && (
                      <span className={styles.metaTag}>🏛️ {projeto.instituicao}</span>
                    )}
                    {projeto.tipo && (
                      <span className={`${styles.metaTag} ${styles.metaTipo}`}>
                        {projeto.tipo}
                      </span>
                    )}
                  </div>
                </div>
                <div className={styles.projetoActions}>
                  <button
                    className={styles.btnEditar}
                    onClick={() => abrirFormEditar(projeto)}
                  >
                    Editar
                  </button>
                  <button
                    className={styles.btnExcluir}
                    onClick={() => setDeleteTarget(projeto)}
                  >
                    Excluir
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── Modal de Confirmação de Exclusão ── */}
      {deleteTarget && (
        <div
          className={styles.confirmOverlay}
          onClick={(e) => { if (e.target === e.currentTarget) setDeleteTarget(null); }}
        >
          <div className={styles.confirmModal}>
            <h3>Excluir projeto?</h3>
            <p>Tem certeza que deseja excluir &quot;{deleteTarget.titulo}&quot;? Esta ação não pode ser desfeita.</p>
            <div className={styles.confirmActions}>
              <button className={styles.btnExcluir} onClick={confirmarExclusao}>
                Excluir
              </button>
              <button className={styles.btnCancelar} onClick={() => setDeleteTarget(null)}>
                Cancelar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
