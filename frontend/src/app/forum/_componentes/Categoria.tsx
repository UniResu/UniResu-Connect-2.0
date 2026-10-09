"use client";

/**
 * Categoria da pergunta: a etiqueta (verde, com o ícone da categoria) que
 * fica logo abaixo do título na lista, na página da pergunta e na página
 * inicial, e o campo de escolha dos formulários. Usa só classes globais
 * (ui-chip, ui-field), para a página inicial não carregar o CSS do fórum.
 */

import type { ReactNode } from "react";
import {
  IconeCapelo,
  IconeDiploma,
  IconeEnvelope,
  IconeMicroscopio,
  IconePessoas,
} from "@/components/ui/Icones";
import { CATEGORIAS, nomeDaCategoria, type CategoriaForum } from "./forum";

const ICONE_DA_CATEGORIA: Record<CategoriaForum, ReactNode> = {
  pesquisa: <IconeMicroscopio />,
  extensao: <IconePessoas />,
  bolsas: <IconeDiploma />,
  candidatura: <IconeEnvelope />,
  "vida-universitaria": <IconeCapelo />,
};

export function ChipCategoria({ categoria, className = "" }: { categoria?: string | null; className?: string }) {
  const nome = nomeDaCategoria(categoria);
  if (!nome) return null;
  return (
    <span className={`ui-chip ui-chip-success ${className}`}>
      {ICONE_DA_CATEGORIA[categoria as CategoriaForum]}
      {nome}
    </span>
  );
}

/** Seleção da categoria nos formulários de nova pergunta e de edição. */
export function CampoCategoria({
  id,
  valor,
  onMudar,
}: {
  id: string;
  valor: CategoriaForum | "";
  onMudar: (categoria: CategoriaForum | "") => void;
}) {
  return (
    <div>
      <label htmlFor={id} className="ui-label">
        Categoria
      </label>
      <select
        id={id}
        value={valor}
        onChange={(e) => onMudar(e.target.value as CategoriaForum | "")}
        className="ui-field"
        required
      >
        <option value="" disabled>
          Escolha a categoria
        </option>
        {CATEGORIAS.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nome}
          </option>
        ))}
      </select>
    </div>
  );
}
