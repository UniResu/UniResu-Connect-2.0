"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./projetos.module.css";
import modalStyles from "./modal.module.css";

interface Projeto {
  id: string;
  titulo: string;
  descricao: string;
  instituicao?: string;
  tipo?: string;
  dataPublicacao?: string;
  local?: string;
  area_estudo?: string;
  e_remoto?: boolean;
  modalidade?: string;
  nome_professor?: string;
  email_professor?: string;
}

export default function ProjetosPage() {
  const { token } = useAuth();
  const router = useRouter();
  const [projetos, setProjetos] = useState<Projeto[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [busca, setBusca] = useState("");
  const [areaFiltro, setAreaFiltro] = useState("");
  const [remotoFiltro, setRemotoFiltro] = useState(false);

  // Modal State
  const [selectedProjeto, setSelectedProjeto] = useState<Projeto | null>(null);
  const [emailCandidato, setEmailCandidato] = useState("");
  const [curriculo, setCurriculo] = useState<File | null>(null);
  const [formStatus, setFormStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [formError, setFormError] = useState("");

  const carregarProjetos = useCallback(async () => {
    setIsLoading(true);
    try {
      const params = new URLSearchParams();
      if (busca) params.set("q", busca);
      if (areaFiltro) params.set("area", areaFiltro);
      if (remotoFiltro) params.set("remoto", "true");

      const data = await api.get<Projeto[]>(
        `/api/projetos/buscar?${params.toString()}`,
        { token: token || undefined }
      );
      setProjetos(data);
    } catch {
      setProjetos([]);
    } finally {
      setIsLoading(false);
    }
  }, [busca, areaFiltro, remotoFiltro, token]);

  useEffect(() => {
    carregarProjetos();
  }, [carregarProjetos]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    carregarProjetos();
  }

  function fecharModal() {
    setSelectedProjeto(null);
    setFormStatus("idle");
    setFormError("");
    setCurriculo(null);
    setEmailCandidato("");
  }

  async function handleCandidatar(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      router.push("/login");
      return;
    }
    if (!selectedProjeto) return;
    if (!emailCandidato || !curriculo) {
      setFormError("Preencha o e-mail e anexe o currículo.");
      return;
    }

    setFormStatus("submitting");
    setFormError("");

    const formData = new FormData();
    formData.append("email", emailCandidato);
    formData.append("curriculo", curriculo);

    try {
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${baseUrl}/api/projetos/${selectedProjeto.id}/candidatar`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        let errStr = "Erro ao enviar candidatura";
        try {
          const errData = await res.json();
          errStr = errData.detail || errStr;
        } catch (_) { }
        throw new Error(errStr);
      }

      setFormStatus("success");
      setTimeout(() => {
        fecharModal();
      }, 2500);
    } catch (err: unknown) {
      setFormStatus("error");
      const e = err as Error;
      setFormError(e.message || "Falha ao enviar candidatura ao servidor.");
    }
  }

  return (
    <div className={styles.page}>
      <div className={styles.header}>
        <h1 className={styles.title}>Projetos Acadêmicos</h1>
        <p className={styles.subtitle}>
          Descubra oportunidades de pesquisa e extensão
        </p>
      </div>

      {/* ── Filtros ── */}
      <form onSubmit={handleSearch} className={styles.filters}>
        <div className={styles.searchGroup}>
          <input
            type="text"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
            placeholder="Buscar por título ou descrição..."
            className={styles.searchInput}
          />
          <button type="submit" className={styles.searchButton}>
            Buscar
          </button>
        </div>
        <div className={styles.filterRow}>
          <select
            value={areaFiltro}
            onChange={(e) => setAreaFiltro(e.target.value)}
            className={styles.filterInput}
          >
            <option value="">Áreas de Estudo</option>
            <option value="Ciências Biológicas e da Saúde">Ciências Biológicas e da Saúde</option>
            <option value="Ciências Exatas e da Terra">Ciências Exatas e da Terra</option>
            <option value="Ciências Humanas">Ciências Humanas</option>
            <option value="Ciências Sociais Aplicadas">Ciências Sociais Aplicadas</option>
            <option value="Área de Tecnologias">Área de Tecnologias</option>
            <option value="Engenharias">Engenharias</option>
            <option value="Ciências Agrárias">Ciências Agrárias</option>
            <option value="Artes e Design">Artes e Design</option>
            <option value="Linguística e Letras">Linguística e Letras</option>
          </select>
          <label className={styles.checkboxLabel}>
            <input
              type="checkbox"
              checked={remotoFiltro}
              onChange={(e) => setRemotoFiltro(e.target.checked)}
              className={styles.checkbox}
            />
            Remoto
          </label>
        </div>
      </form>

      {/* ── Lista de Projetos ── */}
      {isLoading ? (
        <div className={styles.loadingGrid}>
          {[1, 2, 3].map((i) => (
            <div key={i} className={styles.skeletonCard} />
          ))}
        </div>
      ) : projetos.length === 0 ? (
        <div className={styles.emptyState}>
          <span className={styles.emptyIcon}>📭</span>
          <h3>Nenhum projeto encontrado</h3>
          <p>Tente ajustar seus filtros de busca.</p>
        </div>
      ) : (
        <div className={styles.projetosList}>
          {projetos.map((projeto, i) => (
            <article
              key={projeto.id}
              className={styles.projetoCard}
              style={{ animationDelay: `${i * 0.06}s`, cursor: "pointer" }}
              onClick={() => setSelectedProjeto(projeto)}
            >
              <div className={styles.projetoContent}>
                <h3 className={styles.projetoTitulo}>{projeto.titulo}</h3>
                <p className={styles.projetoDesc}>{projeto.descricao}</p>
              </div>
              <div className={styles.projetoMeta}>
                {projeto.instituicao && (
                  <span className={styles.metaTag}>🏛️ {projeto.instituicao}</span>
                )}
                {projeto.tipo && (
                  <span className={styles.metaTag}>{projeto.tipo}</span>
                )}
                {projeto.e_remoto && (
                  <span className={`${styles.metaTag} ${styles.metaRemoto}`}>
                    🌐 Remoto
                  </span>
                )}
                {projeto.dataPublicacao && (
                  <span className={styles.metaDate}>{projeto.dataPublicacao}</span>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      {/* ── Modal de Detalhes e Candidatura ── */}
      {selectedProjeto && (
        <div className={modalStyles.overlay} onClick={(e) => {
          if (e.target === e.currentTarget) fecharModal();
        }}>
          <div className={modalStyles.modal}>
            <button className={modalStyles.closeButton} onClick={fecharModal}>
              &times;
            </button>
            <h2 className={modalStyles.title}>{selectedProjeto.titulo}</h2>

            <div className={modalStyles.infoGrid}>
              {selectedProjeto.instituicao && (
                <div className={modalStyles.infoLine}><strong>Instituição:</strong> {selectedProjeto.instituicao}</div>
              )}
              {selectedProjeto.nome_professor && (
                <div className={modalStyles.infoLine}><strong>Professor/Pesquisador:</strong> {selectedProjeto.nome_professor}</div>
              )}
              {selectedProjeto.local && (
                <div className={modalStyles.infoLine}><strong>Localização:</strong> {selectedProjeto.local}</div>
              )}
              {selectedProjeto.modalidade && (
                <div className={modalStyles.infoLine}><strong>Modalidade:</strong> {selectedProjeto.modalidade}</div>
              )}
              {selectedProjeto.tipo && (
                <div className={modalStyles.infoLine}><strong>Tipo:</strong> {selectedProjeto.tipo}</div>
              )}
            </div>

            <div className={modalStyles.descriptionSection}>
              <h4>Descrição:</h4>
              <p className={modalStyles.descriptionP}>{selectedProjeto.descricao}</p>
            </div>

            <div className={modalStyles.divider} />

            <div className={modalStyles.candidaturaSection}>
              <h4>Candidatar-se</h4>

              {formStatus === "success" ? (
                <div className={modalStyles.successMessage}>
                  Sua candidatura foi enviada com sucesso para o e-mail do responsável! ✅
                </div>
              ) : (
                <form onSubmit={handleCandidatar}>
                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label}>Seu e-mail</label>
                    <input
                      type="email"
                      required
                      className={modalStyles.input}
                      value={emailCandidato}
                      onChange={(e) => setEmailCandidato(e.target.value)}
                    />
                  </div>

                  <div className={modalStyles.formGroup}>
                    <label className={modalStyles.label}>Anexar currículo (PDF ou DOCX)</label>
                    <div className={modalStyles.fileInputWrapper}>
                      <input
                        type="file"
                        accept=".pdf,.doc,.docx"
                        required
                        className={modalStyles.fileInput}
                        onChange={(e) => {
                          if (e.target.files && e.target.files[0]) {
                            setCurriculo(e.target.files[0]);
                          }
                        }}
                      />
                    </div>
                  </div>

                  {formStatus === "error" && (
                    <div className={modalStyles.errorMessage}>{formError}</div>
                  )}

                  <button
                    type={token ? "submit" : "button"}
                    className={modalStyles.submitBtn}
                    disabled={formStatus === "submitting"}
                    onClick={(e) => {
                      if (!token) {
                        e.preventDefault();
                        router.push("/login");
                      }
                    }}
                  >
                    {!token 
                      ? "Faça login para se candidatar" 
                      : formStatus === "submitting" ? "Enviando..." : "Candidatar-se"}
                  </button>
                </form>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
