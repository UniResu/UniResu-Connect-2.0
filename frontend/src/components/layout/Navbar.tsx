"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import ThemeToggle from "@/components/ui/ThemeToggle";
import { IconeSetaBaixo } from "@/components/ui/Icones";
import styles from "./Navbar.module.css";

const LINKS = [
  { href: "/", label: "Início" },
  { href: "/#quem-somos", label: "Quem somos" },
  { href: "/projetos", label: "Projetos acadêmicos" },
  { href: "/forum", label: "Fórum" },
];

/** Página atual: "Início" só na raiz; "Quem somos" é uma âncora da página
 *  inicial e não marca; as outras valem também para as subpáginas. */
function estaEm(pathname: string, href: string) {
  if (href === "/") return pathname === "/";
  if (href.includes("#")) return false;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function Navbar() {
  const pathname = usePathname();
  // O menu mobile vive em um componente remontado a cada rota (key): ao
  // navegar, por link, redirect ou botão voltar/avançar, ele nasce fechado.
  return <NavbarConteudo key={pathname} pathname={pathname} />;
}

function NavbarConteudo({ pathname }: { pathname: string }) {
  const { user, isAuthenticated, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isProfessorOuPesquisador =
    user?.papel === "professor" || user?.papel === "pesquisador";
  const primeiroNome = user?.nome_social?.split(" ")[0] || user?.nome?.split(" ")[0] || "";
  const inicial = (user?.nome_social || user?.nome || "U").charAt(0).toUpperCase();

  // Fecha o dropdown ao clicar fora
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Menu mobile: fecha com Esc, trava a rolagem enquanto aberto e fecha se a
  // tela passar à largura de desktop (onde o menu e o hambúrguer somem pelo
  // CSS; sem isto a trava de rolagem ficaria presa).
  useEffect(() => {
    if (!menuOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false);
    }
    const desktop = window.matchMedia("(min-width: 769px)");
    function handleDesktop(e: MediaQueryListEvent) {
      if (e.matches) setMenuOpen(false);
    }
    document.addEventListener("keydown", handleKey);
    desktop.addEventListener("change", handleDesktop);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      desktop.removeEventListener("change", handleDesktop);
      document.body.style.overflow = overflowAnterior;
    };
  }, [menuOpen]);

  const fecharMenu = () => setMenuOpen(false);

  return (
    <header className={styles.header}>
      <nav className={styles.navbar} aria-label="Principal">
        <Link href="/" className={styles.logo} onClick={fecharMenu} aria-label="UniResu Connect, página inicial">
          <img src="/uniresulogo.png" alt="" className={styles.logoIcon} />
        </Link>

        {/* Links (desktop) */}
        <ul className={styles.navLinks}>
          {LINKS.map((l) => (
            <li key={l.href}>
              <Link href={l.href} aria-current={estaEm(pathname, l.href) ? "page" : undefined}>
                {l.label}
              </Link>
            </li>
          ))}
        </ul>

        {/* Ações (desktop): no celular tudo isso vive dentro do menu hambúrguer */}
        <div className={styles.navActions}>
          <ThemeToggle />
          {isAuthenticated ? (
            <div className={styles.userMenu}>
              <div className={styles.dropdownWrapper} ref={dropdownRef}>
                <button
                  className={styles.avatarButton}
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  aria-expanded={dropdownOpen}
                  aria-haspopup="menu"
                >
                  <div className={styles.avatar}>{inicial}</div>
                  <span className={styles.userName}>{primeiroNome}</span>
                  <span className={`${styles.dropdownArrow} ${dropdownOpen ? styles.dropdownArrowAberta : ""}`}>
                    <IconeSetaBaixo tamanho={16} />
                  </span>
                </button>

                {dropdownOpen && (
                  <div className={styles.dropdownMenu} role="menu">
                    <Link href="/perfil" className={styles.dropdownItem} onClick={() => setDropdownOpen(false)}>
                      Perfil
                    </Link>
                    {isProfessorOuPesquisador ? (
                      <Link href="/projetos/gerenciar" className={styles.dropdownItem} onClick={() => setDropdownOpen(false)}>
                        Meus Projetos
                      </Link>
                    ) : (
                      <Link href="/candidaturas" className={styles.dropdownItem} onClick={() => setDropdownOpen(false)}>
                        Candidaturas
                      </Link>
                    )}
                    <div className={styles.dropdownDivider} />
                    <button
                      className={styles.dropdownItemLogout}
                      onClick={() => {
                        setDropdownOpen(false);
                        logout();
                      }}
                    >
                      Sair
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className={styles.authButtons}>
              <Link href="/registrar" className={styles.btnSimples}>Registre-se</Link>
              <Link href="/login" className={styles.btnDestaque}>Entrar</Link>
            </div>
          )}
        </div>

        {/* Com o nome escrito: só o ícone, muita gente não reconhecia o menu e
            rolava a página procurando as opções. O texto visível é o nome do
            botão; aria-expanded diz se está aberto. */}
        <button
          type="button"
          className={`${styles.hamburger} ${menuOpen ? styles.hamburgerOpen : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-expanded={menuOpen}
          aria-controls="menu-mobile"
        >
          <span className={styles.hamburgerRotulo}>{menuOpen ? "Fechar" : "Menu"}</span>
          <span className={styles.barras} aria-hidden="true">
            <span />
            <span />
            <span />
          </span>
        </button>
      </nav>

      {/* Menu mobile: links + conta, tudo num lugar só */}
      <div
        id="menu-mobile"
        className={`${styles.mobileMenu} ${menuOpen ? styles.mobileMenuOpen : ""}`}
        aria-hidden={!menuOpen}
      >
        <ul className={styles.mobileLinks}>
          {LINKS.map((l) => (
            <li key={l.href}>
              <Link
                href={l.href}
                onClick={fecharMenu}
                tabIndex={menuOpen ? 0 : -1}
                aria-current={estaEm(pathname, l.href) ? "page" : undefined}
              >
                {l.label}
              </Link>
            </li>
          ))}
        </ul>

        <div className={styles.mobileDivider} />

        <ThemeToggle rotulado className={styles.mobileTema} />

        <div className={styles.mobileDivider} />

        {isAuthenticated ? (
          <div className={styles.mobileAccount}>
            <div className={styles.mobileUser}>
              <div className={styles.avatar}>{inicial}</div>
              <div>
                <p className={styles.mobileUserName}>{user?.nome_social || user?.nome}</p>
                {user?.instituicao && <p className={styles.mobileUserMeta}>{user.instituicao}</p>}
              </div>
            </div>
            <Link href="/perfil" className={styles.mobileItem} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
              Perfil
            </Link>
            {isProfessorOuPesquisador ? (
              <Link href="/projetos/gerenciar" className={styles.mobileItem} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
                Meus Projetos
              </Link>
            ) : (
              <Link href="/candidaturas" className={styles.mobileItem} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
                Candidaturas
              </Link>
            )}
            <button
              className={styles.mobileLogout}
              onClick={() => {
                fecharMenu();
                logout();
              }}
              tabIndex={menuOpen ? 0 : -1}
            >
              Sair
            </button>
          </div>
        ) : (
          <div className={styles.mobileAuth}>
            <Link href="/registrar" className={styles.mobileBtnSimples} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
              Registre-se
            </Link>
            <Link href="/login" className={styles.mobileBtnDestaque} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
              Entrar
            </Link>
          </div>
        )}
      </div>

      {menuOpen && <div className={styles.backdrop} onClick={fecharMenu} aria-hidden="true" />}
    </header>
  );
}
