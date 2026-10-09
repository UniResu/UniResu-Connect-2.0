"use client";

/**
 * Detalhe de um projeto: descrição, dados da fonte, link para o portal de
 * origem e a candidatura. Usado no modal da busca (/projetos) e na página
 * própria de cada projeto (/projetos/[id]), que os buscadores indexam.
 */

import { memo, useEffect, useId, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { User } from "@/types/user";
import { formatarData, formatarSituacao, moduloDoProjeto, tomDaSituacao, type Projeto } from "@/types/projeto";
import { Icone } from "./Icone";
import m from "../modal.module.css";

/** Fontes que não publicam o e-mail de cada coordenação, mas têm um contato geral. */
const CONTATO_GERAL: Record<string, { rotulo: string; email: string }> = {
  "ufv:extensao": { rotulo: "Registro de Atividades de Extensão da UFV (RAEX)", email: "raex@ufv.br" },
};

/** Aviso mostrado no lugar do formulário quando o projeto não tem e-mail de contato. */
function avisoSemContato(p: Projeto) {
  const geral = CONTATO_GERAL[`${p.origem}:${p.modulo}`];
  if (geral) {
    return (
      <>
        A UFV não divulga o e-mail de cada coordenação nos dados abertos, então a candidatura por aqui
        fica indisponível. O contato geral é o {geral.rotulo}:{" "}
        <a href={`mailto:${geral.email}`}>{geral.email}</a>. Cite o título do projeto na mensagem.
      </>
    );
  }
  if (p.origem === "puccamp") {
    return (
      <>
        A PUC-Campinas não divulga o e-mail de cada docente na página de extensão, então a candidatura por
        aqui fica indisponível. Use o botão acima para ver o projeto no portal da universidade ou procure a
        faculdade indicada.
      </>
    );
  }
  if (p.origem === "ufv") {
    return (
      <>
        A UFV não divulga o e-mail de cada coordenação nos dados abertos. Use a página do projeto no
        sistema de pesquisa da UFV (link acima) ou procure o departamento indicado.
      </>
    );
  }
  return (
    <>
      Projeto ainda sem contato cadastrado. Assim que o e-mail da coordenação for cadastrado, você
      poderá enviar sua carta de intenção por aqui.
    </>
  );
}

/** Nome da fonte externa, para o botão "Ver no SIGAA". */
const FONTE_NOME: Record<string, string> = {
  sigaa: "SIGAA",
  unirio: "Portal da UNIRIO",
  ufv: "Portal da UFV",
  puccamp: "portal da PUC-Campinas",
};

const CARTA_MIN = 300;
const CARTA_MAX = 5000;

const CARTA_PLACEHOLDER = `Quem sou: curso, período e o que já estudei ou fiz que tem relação com o projeto.

Por que este projeto: o que me interessa nele e como posso contribuir.

Disponibilidade: quantas horas por semana, em quais turnos e a partir de quando.`;

function cursoPeriodoDoUsuario(user: User | null) {
  if (!user?.curso) return "";
  const semestre = user.dados_aluno?.semestre;
  return semestre ? `${user.curso}, ${semestre}º período` : user.curso;
}

/** Converte o `detail` da API (string ou lista de erros do FastAPI) em texto. */
function mensagemDeErro(detail: unknown, padrao: string) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { msg?: string }) => (d.msg || "").replace(/^Value error, /, ""))
      .filter(Boolean)
      .join(" ") || padrao;
  }
  return padrao;
}

/* ═══════════════════════════════════════════
   Detalhe do projeto (corpo do modal)
   ═══════════════════════════════════════════ */

function Secao({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <section className={m.secao}>
      <h3 className={m.secaoTitulo}>{titulo}</h3>
      {children}
    </section>
  );
}

export const DetalheProjeto = memo(function DetalheProjeto({
  projeto: p,
  onFechar,
  naPagina = false,
}: {
  projeto: Projeto;
  /** No modal: fecha depois de uma candidatura enviada. */
  onFechar?: () => void;
  /** Na página própria do projeto (fora do modal). */
  naPagina?: boolean;
}) {
  const { token, user } = useAuth();
  const router = useRouter();
  const modulo = moduloDoProjeto(p);
  const situacao = formatarSituacao(p.situacao);
  const tom = tomDaSituacao(p.situacao);

  const metadados: { rotulo: string; valor: ReactNode }[] = [];
  if (p.nome_professor) {
    metadados.push({ rotulo: p.origem ? "Coordenação" : "Docente ou pesquisador(a)", valor: p.nome_professor });
  }
  if (p.responsavel_acao && p.responsavel_acao !== p.nome_professor) {
    metadados.push({ rotulo: "Responsável pela ação", valor: p.responsavel_acao });
  }
  if (p.categoria && p.origem) metadados.push({ rotulo: "Categoria", valor: p.categoria });
  if (p.instituicao) metadados.push({ rotulo: "Instituição", valor: p.instituicao });
  if (p.campus) metadados.push({ rotulo: "Campus", valor: p.campus });
  if (p.unidade) metadados.push({ rotulo: "Unidade ou departamento", valor: p.unidade });
  if (p.area_conhecimento) metadados.push({ rotulo: "Área do conhecimento", valor: p.area_conhecimento });
  if (p.area_tematica) metadados.push({ rotulo: "Área temática", valor: p.area_tematica });
  if (situacao) {
    metadados.push({
      rotulo: "Situação",
      valor: (
        <span className={`${m.situacao} ${m[`tom_${tom}`]}`}>
          <span className={m.ponto} aria-hidden="true" />
          {situacao}
        </span>
      ),
    });
  }
  if (p.periodo_inicio && p.periodo_fim) {
    metadados.push({ rotulo: "Período", valor: `${formatarData(p.periodo_inicio)} a ${formatarData(p.periodo_fim)}` });
  }
  if (p.ano) metadados.push({ rotulo: "Ano", valor: p.ano });
  if (p.codigo && p.origem === "sigaa") metadados.push({ rotulo: "Código no SIGAA", valor: p.codigo });
  if (p.modalidade) metadados.push({ rotulo: "Modalidade", valor: p.modalidade });
  if (p.local) metadados.push({ rotulo: "Localização", valor: p.local });

  // Celular e tablet: a candidatura fica no fim da rolagem, então uma barra
  // fixa no rodapé do modal leva até ela. A barra vem depois da seção no DOM
  // (gruda no rodapé enquanto não chega a vez dela) e some quando a seção
  // aparece; o espaço que ela deixa fica no fim do modal.
  const candidaturaRef = useRef<HTMLElement>(null);
  const [candidaturaVisivel, setCandidaturaVisivel] = useState(false);
  useEffect(() => {
    const alvo = candidaturaRef.current;
    if (!alvo || typeof IntersectionObserver === "undefined") return;
    const observador = new IntersectionObserver(([entrada]) => setCandidaturaVisivel(entrada.isIntersecting), {
      threshold: 0.1,
    });
    observador.observe(alvo);
    return () => observador.disconnect();
  }, []);

  function irParaCandidatura() {
    const alvo = candidaturaRef.current;
    if (!alvo) return;
    alvo.scrollIntoView({ behavior: "smooth", block: "start" });
    alvo.querySelector<HTMLElement>("h3")?.focus({ preventScroll: true });
  }

  const linkFonte = p.link_detalhe || p.link_consulta;
  const rotuloFonte = p.link_detalhe ? `Ver no ${FONTE_NOME[p.origem || ""] || "site de origem"}` : "Buscar no SIGAA";

  const temConteudoPrincipal = Boolean(
    p.descricao ||
      (p.palavras_chave && p.palavras_chave.length > 0) ||
      (p.linhas_extensao && p.linhas_extensao.length > 0) ||
      p.grupo_pesquisa ||
      p.financiamento
  );

  return (
    <>
      <div className={m.corpo}>
        <div className={m.principal}>
          <div className={m.chips}>
            {p.tipo && (
              <span
                className={`ui-chip ${
                  modulo === "pesquisa" ? "ui-chip-primary" : modulo === "extensao" ? "ui-chip-info" : ""
                }`}
              >
                {p.tipo}
              </span>
            )}
            {p.e_remoto && <span className="ui-chip ui-chip-success">Remoto</span>}
          </div>

          {p.descricao && (
            <Secao titulo="Descrição">
              <p className={m.texto}>{p.descricao}</p>
            </Secao>
          )}
          {p.palavras_chave && p.palavras_chave.length > 0 && (
            <Secao titulo="Palavras-chave">
              <ul className={m.listaChips}>
                {p.palavras_chave.map((palavra) => (
                  <li key={palavra} className="ui-chip">
                    {palavra}
                  </li>
                ))}
              </ul>
            </Secao>
          )}
          {p.linhas_extensao && p.linhas_extensao.length > 0 && (
            <Secao titulo="Linhas de extensão">
              <ul className={m.listaTexto}>
                {p.linhas_extensao.map((linha) => (
                  <li key={linha}>{linha}</li>
                ))}
              </ul>
            </Secao>
          )}
          {p.grupo_pesquisa && (
            <Secao titulo="Grupo de pesquisa">
              <p className={m.texto}>{p.grupo_pesquisa}</p>
            </Secao>
          )}
          {p.financiamento && (
            <Secao titulo="Financiamento">
              <p className={m.texto}>{p.financiamento}</p>
            </Secao>
          )}
          {!temConteudoPrincipal && (
            <p className={m.semDescricao}>A fonte não publicou descrição para este projeto.</p>
          )}
        </div>

        <aside className={m.lateral} aria-label="Dados do projeto">
          {metadados.length > 0 && (
            <dl className={m.meta}>
              {metadados.map((item) => (
                <div key={item.rotulo} className={m.metaItem}>
                  <dt>{item.rotulo}</dt>
                  <dd>{item.valor}</dd>
                </div>
              ))}
            </dl>
          )}
          {p.link_detalhe ? (
            <a
              href={p.link_detalhe}
              target="_blank"
              rel="noopener noreferrer"
              className={`ui-btn ui-btn-secondary ${m.linkFonte}`}
            >
              Ver no {FONTE_NOME[p.origem || ""] || "site de origem"}
              <Icone nome="linkExterno" tamanho={16} />
            </a>
          ) : p.link_consulta ? (
            // Pesquisa no SIGAA não tem página pública por projeto: o botão abre a
            // consulta da instituição e a dica diz o que digitar lá.
            <div className={m.linkConsulta}>
              <a
                href={p.link_consulta}
                target="_blank"
                rel="noopener noreferrer"
                className={`ui-btn ui-btn-secondary ${m.linkFonte}`}
              >
                Buscar no SIGAA
                <Icone nome="linkExterno" tamanho={16} />
              </a>
              <p className={m.linkConsultaDica}>
                {p.codigo ? (
                  <>
                    Na consulta pública, procure pelo código <strong>{p.codigo}</strong> ou pelo título.
                  </>
                ) : (
                  <>Na consulta pública, procure pelo título do projeto.</>
                )}
              </p>
            </div>
          ) : null}
          {/* No modal: endereço próprio do projeto, para compartilhar. */}
          {!naPagina && (
            <Link href={`/projetos/${encodeURIComponent(p.id)}`} className={`ui-btn ui-btn-ghost ${m.linkPagina}`}>
              Página do projeto
            </Link>
          )}
        </aside>
      </div>

      <section ref={candidaturaRef} className={`ui-card ${m.candidatura}`} aria-labelledby="candidatura-titulo">
        <h3 id="candidatura-titulo" className={m.candidaturaTitulo} tabIndex={-1}>
          Candidatar-se
        </h3>

        {!p.tem_contato ? (
          <>
            <div className={m.aviso}>
              <Icone nome="info" className={m.avisoIcone} />
              <p>{avisoSemContato(p)}</p>
            </div>
            <button type="button" className="ui-btn ui-btn-primary" disabled>
              Candidatar-se
            </button>
          </>
        ) : !token ? (
          <>
            <p className={m.candidaturaTexto}>
              Entre na sua conta para enviar uma carta de intenção à coordenação deste projeto.
            </p>
            <button type="button" className="ui-btn ui-btn-primary" onClick={() => router.push("/login")}>
              Faça login para se candidatar
            </button>
          </>
        ) : (
          <FormularioCandidatura key={user?.id ?? "anonimo"} projeto={p} onEnviado={onFechar} />
        )}
      </section>

      <div
        className={`${m.atalho} ${naPagina ? m.atalhoPagina : ""} ${candidaturaVisivel ? m.atalhoOculto : ""}`}
        aria-hidden={candidaturaVisivel}
      >
        <button
          type="button"
          className="ui-btn ui-btn-primary"
          onClick={irParaCandidatura}
          tabIndex={candidaturaVisivel ? -1 : 0}
        >
          Candidatar-se
        </button>
        {linkFonte && (
          <a
            href={linkFonte}
            target="_blank"
            rel="noopener noreferrer"
            className={`ui-btn ui-btn-secondary ${m.atalhoFonte}`}
            aria-label={rotuloFonte}
            title={rotuloFonte}
            tabIndex={candidaturaVisivel ? -1 : 0}
          >
            <Icone nome="linkExterno" tamanho={18} />
          </a>
        )}
      </div>
    </>
  );
});

/* ═══════════════════════════════════════════
   Formulário de candidatura (estado local: digitar na carta não refaz o modal)
   ═══════════════════════════════════════════ */

function FormularioCandidatura({ projeto, onEnviado }: { projeto: Projeto; onEnviado?: () => void }) {
  const { token, user } = useAuth();
  const router = useRouter();
  const idBase = useId();

  // Pré-preenche com o que já sabemos do aluno logado.
  const [nome, setNome] = useState(user?.nome_social || user?.nome || "");
  const [cursoPeriodo, setCursoPeriodo] = useState(cursoPeriodoDoUsuario(user));
  const [emailCandidato, setEmailCandidato] = useState(user?.email || "");
  const [lattes, setLattes] = useState("");
  const [carta, setCarta] = useState("");
  const [formStatus, setFormStatus] = useState<"idle" | "submitting" | "success" | "error">("idle");
  const [formError, setFormError] = useState("");

  // Depois do envio, o modal fecha sozinho em alguns segundos (na página
  // própria do projeto a mensagem de sucesso fica).
  useEffect(() => {
    if (formStatus !== "success" || !onEnviado) return;
    const t = setTimeout(onEnviado, 3000);
    return () => clearTimeout(t);
  }, [formStatus, onEnviado]);

  async function handleCandidatar(e: React.FormEvent) {
    e.preventDefault();
    if (!token) {
      router.push("/login");
      return;
    }
    if (user?.perfil_completo === false) {
      // Conta do ORCID que ainda não escolheu o vínculo nem aceitou as regras:
      // a API recusa a candidatura (403) até concluir o perfil.
      router.push("/perfil/completar");
      return;
    }
    if (carta.trim().length < CARTA_MIN) {
      setFormStatus("error");
      setFormError(`A carta de intenção precisa ter pelo menos ${CARTA_MIN} caracteres.`);
      return;
    }

    setFormStatus("submitting");
    setFormError("");

    try {
      await api.post(
        `/api/projetos/${projeto.id}/candidatar`,
        {
          nome,
          curso_periodo: cursoPeriodo,
          email: emailCandidato,
          lattes_url: lattes.trim() || null,
          carta,
        },
        { token }
      );
      setFormStatus("success");
    } catch (err: unknown) {
      setFormStatus("error");
      const apiErr = err as { detail?: unknown };
      setFormError(mensagemDeErro(apiErr.detail, "Falha ao enviar candidatura ao servidor."));
    }
  }

  if (formStatus === "success") {
    return (
      <div className={m.sucesso} role="status">
        <Icone nome="check" className={m.sucessoIcone} />
        <p>
          Sua carta de intenção foi enviada à coordenação do projeto!
          <br />
          Enviamos uma cópia para o e-mail da sua conta.
        </p>
      </div>
    );
  }

  const tamanhoCarta = carta.trim().length;
  const cartaOk = tamanhoCarta >= CARTA_MIN;

  return (
    <form onSubmit={handleCandidatar} className={m.form}>
      <div className={m.linhaCampos}>
        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-nome`}>
            Nome completo
          </label>
          <input
            id={`${idBase}-nome`}
            type="text"
            required
            minLength={3}
            maxLength={120}
            className="ui-field"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            autoComplete="name"
          />
        </div>

        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-curso`}>
            Curso e período
          </label>
          <input
            id={`${idBase}-curso`}
            type="text"
            required
            minLength={2}
            maxLength={120}
            placeholder="Ex.: Ciência da Computação, 5º período"
            className="ui-field"
            value={cursoPeriodo}
            onChange={(e) => setCursoPeriodo(e.target.value)}
          />
        </div>
      </div>

      <div className={m.linhaCampos}>
        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-email`}>
            Seu e-mail
          </label>
          <input
            id={`${idBase}-email`}
            type="email"
            required
            className="ui-field"
            value={emailCandidato}
            onChange={(e) => setEmailCandidato(e.target.value)}
            autoComplete="email"
          />
          <p className="ui-hint">A resposta da coordenação chegará neste e-mail.</p>
        </div>

        <div className={m.campo}>
          <label className="ui-label" htmlFor={`${idBase}-lattes`}>
            Link do Currículo Lattes <span className={m.opcional}>(opcional)</span>
          </label>
          <input
            id={`${idBase}-lattes`}
            type="url"
            maxLength={300}
            placeholder="http://lattes.cnpq.br/0000000000000000"
            className="ui-field"
            value={lattes}
            onChange={(e) => setLattes(e.target.value)}
          />
        </div>
      </div>

      <div className={m.campo}>
        <label className="ui-label" htmlFor={`${idBase}-carta`}>
          Carta de intenção
        </label>
        <textarea
          id={`${idBase}-carta`}
          required
          rows={9}
          maxLength={CARTA_MAX}
          placeholder={CARTA_PLACEHOLDER}
          className={`ui-field ${m.carta}`}
          value={carta}
          onChange={(e) => setCarta(e.target.value)}
        />
        <p className={`ui-hint ${m.contador} ${cartaOk ? m.contadorOk : ""}`} aria-live="polite">
          {cartaOk ? (
            <>
              <Icone nome="check" tamanho={14} />
              {tamanhoCarta} caracteres
            </>
          ) : (
            `${tamanhoCarta} de ${CARTA_MIN} caracteres (faltam ${CARTA_MIN - tamanhoCarta})`
          )}
        </p>
      </div>

      {formStatus === "error" && (
        <div className={m.erro} role="alert">
          {formError}
        </div>
      )}

      <div className={m.acoes}>
        <button type="submit" className="ui-btn ui-btn-primary" disabled={formStatus === "submitting"}>
          {formStatus === "submitting" ? "Enviando" : "Enviar carta de intenção"}
        </button>
      </div>
    </form>
  );
}
