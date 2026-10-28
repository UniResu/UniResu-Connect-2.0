import styles from "./CaixaOpcao.module.css";

interface CaixaOpcaoProps {
  marcada: boolean;
  onMudar: (marcada: boolean) => void;
  titulo: string;
  descricao: string;
}

/**
 * Caixa de marcar em destaque: o cartão inteiro é clicável, com a caixa
 * maior que a dos aceites, o título em negrito e uma linha de explicação.
 * Usada no "Não tenho e-mail institucional" do registro, que precisa ser
 * vista antes dos campos de e-mail.
 */
export default function CaixaOpcao({ marcada, onMudar, titulo, descricao }: CaixaOpcaoProps) {
  return (
    <label className={`${styles.caixa} ${marcada ? styles.marcada : ""}`}>
      <input type="checkbox" checked={marcada} onChange={(e) => onMudar(e.target.checked)} />
      <span className={styles.texto}>
        <span className={styles.titulo}>{titulo}</span>
        <span className={styles.descricao}>{descricao}</span>
      </span>
    </label>
  );
}
