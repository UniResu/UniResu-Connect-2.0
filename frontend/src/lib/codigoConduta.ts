import { EMAIL_CONTATO } from "@/lib/constants";

/**
 * Textos mostrados nos modais do registro e do perfil: o código de conduta
 * (as "regras de utilização e convivência") e a nota sobre os dados.
 */

export const CODIGO_CONDUTA_TITULO = "Código de conduta da plataforma";

export const CODIGO_CONDUTA_INTRODUCAO =
  "O UniResu Connect reúne estudantes, docentes e pesquisadores de várias instituições. Para que a convivência funcione, quem usa a plataforma concorda com os pontos abaixo.";

export const CODIGO_CONDUTA: string[] = [
  "Trate todas as pessoas com respeito, nas mensagens do fórum, nas cartas de intenção e em qualquer contato feito a partir daqui.",
  "Não são aceitos assédio, discriminação, ameaças ou exposição de dados de terceiros, em nenhuma forma.",
  "O fórum e as cartas de intenção não são espaço para propaganda, spam, venda de serviços ou divulgação sem relação com a vida acadêmica.",
  "Honestidade acadêmica: não se apresente com vínculo, titulação ou autoria que não tenha, e não envie uma mesma carta de intenção em massa.",
  "Os contatos das coordenações dos projetos servem apenas para tratar do próprio projeto; usá-los para outros fins é motivo de remoção da conta.",
  "Conteúdos ou cartas de intenção que violem estas regras podem ser removidos pela moderação, e a conta pode ser suspensa ou encerrada, com aviso por e-mail.",
  `Dúvidas e denúncias podem ser enviadas à equipe pelo e-mail ${EMAIL_CONTATO}, que também está no rodapé do site; a resposta chega em até alguns dias úteis.`,
];

export const DADOS_TITULO = "Como os seus dados são usados";

export const DADOS_TEXTO: string[] = [
  "As coordenações dos projetos que você contatar recebem a sua carta de intenção, o seu nome, o seu e-mail de contato e os dados que já aparecem no seu perfil público.",
  "Não compartilhamos nada além disso, nem com as coordenações dos projetos nem com terceiros.",
  "O e-mail de contato segue apenas para a coordenação do projeto escolhido, junto com a carta de intenção, e você pode apagar a conta quando quiser.",
];
