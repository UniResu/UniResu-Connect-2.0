# Sistema de design do UniResu Connect

Guia curto para quem mexe no frontend. Os tokens vivem em `src/app/globals.css`;
este arquivo explica como usá-los. A meta é um site com cara de produto atual:
superfícies limpas, hierarquia clara, poucos efeitos, consistente em todas as
páginas e nos dois temas (claro e escuro).

## Princípios

1. **Cor só por token.** Nenhum hex, rgb ou nome de cor nos módulos CSS. Tudo
   vem de `var(--...)`, porque o tema escuro troca os tokens e não os módulos.
   Exceções: o cabeçalho e o rodapé, que são escuros nos dois temas e têm os
   próprios tokens (`--header-*`, `--footer-bg`); e as seções escuras da página
   inicial, que usam `--brand-*` e `--text-on-dark*`.
2. **Texto em cor de marca usa `--text-accent`.** `--primary` é fundo de botão
   e, no tema escuro, não tem contraste suficiente como texto.
3. **Raios semânticos.** `--radius-control` (10px) para botão, campo, select,
   item de menu e qualquer coisa que se clica; `--radius-card` (16px) para
   card, painel e caixa de formulário; `--radius-modal` (20px) para modal e
   folha; `--radius-chip` (pílula) para tag, selo, avatar e contador. Nada de
   `--radius-sm/md/lg/xl` direto nos módulos novos nem de valores em px.
4. **Sombra é informação, não decoração.** Card em repouso: borda de 1px
   (`--surface-border`) e `--shadow-sm`. Hover: borda `--surface-border-hover`
   e `--shadow-md`, sem `transform: translateY`. `--shadow-lg` só em menus,
   popovers e dropdowns; `--shadow-xl` só em modais. Nenhum `box-shadow` solto
   com rgba.
5. **Sem vidro em listas.** `backdrop-filter` só no fundo de modal. Cards são
   opacos (`--surface`). `transition: all` é proibido: liste as propriedades.
6. **Fundos suaves.** Página nunca é branco puro: o corpo usa `--bg-primary`.
   Projetos acadêmicos usa `--page-projetos-bg` com brilho `--page-projetos-glow`
   (lilás frio); o fórum usa `--page-forum-bg` com `--page-forum-glow` (papel
   quente). As duas precisam continuar visivelmente diferentes entre si.
7. **Controles iguais em todo lugar.** Botões: classes globais `ui-btn` +
   `ui-btn-primary | ui-btn-secondary | ui-btn-ghost | ui-btn-danger` (+
   `ui-btn-sm`/`ui-btn-lg`). Campos: `ui-field` (input, select, textarea) com
   `ui-label` e `ui-hint`. Cards: `ui-card` (+ `ui-card-hover`). Chips:
   `ui-chip` + variantes. Títulos de página: `ui-page-header`, `ui-page-title`,
   `ui-page-subtitle`. Use as classes globais direto no `className` e deixe no
   módulo só o que é específico da tela (layout, espaçamentos).
8. **Altura dos controles:** 2.75rem (44px) no padrão, 2.25rem no `sm`,
   3.25rem no `lg`. Toque confortável no celular.
9. **Tipografia:** Plus Jakarta Sans. Títulos com `letter-spacing: -0.02em`,
   pesos 700/800. Corpo 1rem/1.6. Textos secundários `--text-secondary`,
   legendas `--text-muted`. Sem `text-transform: uppercase` em botões e
   títulos; rótulos em caixa alta só em selos pequenos (`.tipo` do card).
10. **Sem emojis como ícones.** Ícones são SVG inline (traço 2, 20px) ou texto.
11. **Movimento curto.** `--transition-fast` em cor/borda/sombra; animações
    de entrada só no `animate-fade-in`. Respeite `prefers-reduced-motion`
    (já tratado no globals). Única exceção decorativa: a nave da seção do
    fórum na página inicial flutua devagar, porque é a assinatura da marca.
12. **Símbolos da marca com parcimônia.** Os ícones espaciais de
    `components/ui/Icones` (nave, alienígena, planeta, foguete, estrelas)
    entram em estados vazios, cabeçalhos de seção e telas de entrada, nunca
    como decoração repetida em listas.
13. **Acessibilidade:** foco visível (`:focus-visible` com `--ring`), rótulos
    em todo controle, contraste AA nos dois temas, nada que dependa só de cor.

## Tema escuro

O `<html>` recebe `data-theme="light" | "dark"` antes da primeira pintura
(script inline em `layout.tsx`, preferência em `localStorage`, senão a do
sistema). O botão `ThemeToggle` (cabeçalho e menu do celular) alterna. Para
um módulo funcionar nos dois temas basta usar tokens; se precisar de algo
específico do escuro, use `:global([data-theme="dark"]) .classe { ... }`.

## Componentes compartilhados

- `components/projetos/ProjetoCard`: o card de projeto, usado na busca e na
  página inicial (`compacto` para a inicial). Clique no card inteiro.
- `components/ui/Modal`: diálogo com Esc, clique fora e foco preso.
- `components/ui/MultiSelect`: seleção múltipla com "Todos" e "Limpar seleção".
- `components/ui/ThemeToggle`: botão de tema.
- `components/layout/Navbar` e `Footer`: escuros nos dois temas.

## Checklist antes de entregar uma tela

- [ ] Nenhum hex/rgb no módulo (grep `#[0-9a-f]{3,6}` e `rgba?(`).
- [ ] Raios só pelos quatro tokens semânticos.
- [ ] Sombras só pelos tokens e segundo a regra 4.
- [ ] Sem `transition: all`, sem `backdrop-filter` em listas, sem `translateY` no hover.
- [ ] Botões e campos com as classes `ui-*`.
- [ ] Tema escuro conferido (data-theme="dark"): texto legível, bordas visíveis.
- [ ] Celular a 390px sem rolagem horizontal; alvos de toque de 44px.
- [ ] `npx tsc --noEmit -p .` e `npx eslint <arquivos>` limpos.
