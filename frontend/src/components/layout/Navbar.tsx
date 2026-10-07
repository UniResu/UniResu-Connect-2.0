"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./Navbar.module.css";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/#quem-somos", label: "Quem somos" },
  { href: "/projetos", label: "Projetos acadêmicos" },
  { href: "/forum", label: "Fórum" },
];

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const pathname = usePathname();
  // O menu mobile guarda a rota em que foi aberto: ao navegar, fecha sozinho
  // (derivado no render, sem efeito).
  const [menuAbertoEm, setMenuAbertoEm] = useState<string | null>(null);
  const menuOpen = menuAbertoEm === pathname;
  const setMenuOpen = (aberto: boolean) => setMenuAbertoEm(aberto ? pathname : null);
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

  // Menu mobile: fecha com Esc e trava a rolagem enquanto aberto.
  useEffect(() => {
    if (!menuOpen) return;
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuAbertoEm(null);
    }
    document.addEventListener("keydown", handleKey);
    const overflowAnterior = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = overflowAnterior;
    };
  }, [menuOpen]);

  const fecharMenu = () => setMenuOpen(false);

  return (
    <header className={styles.header}>
      <nav className={styles.navbar} aria-label="Principal">
        <Link href="/" className={styles.logo} onClick={fecharMenu}>
          <img src="/uniresulogo.png" alt="Logo Uniresu" className={styles.logoIcon} />
        </Link>

        {/* Links (desktop) */}
        <ul className={styles.navLinks}>
          {LINKS.map((l) => (
            <li key={l.href}><Link href={l.href}>{l.label}</Link></li>
          ))}
        </ul>

        {/* Ações (desktop): no celular tudo isso vive dentro do menu hambúrguer */}
        <div className={styles.navActions}>
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
                  <span className={styles.dropdownArrow}>▾</span>
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
              <Link href="/login" className={styles.btnLogin}>Entrar</Link>
              <Link href="/registrar" className={styles.btnRegister}>Registre-se</Link>
            </div>
          )}
        </div>

        <button
          className={`${styles.hamburger} ${menuOpen ? styles.hamburgerOpen : ""}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? "Fechar menu" : "Abrir menu"}
          aria-expanded={menuOpen}
          aria-controls="menu-mobile"
        >
          <span />
          <span />
          <span />
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
              <Link href={l.href} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>{l.label}</Link>
            </li>
          ))}
        </ul>

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
            <Link href="/login" className={styles.mobileBtnLogin} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
              Entrar
            </Link>
            <Link href="/registrar" className={styles.mobileBtnRegister} onClick={fecharMenu} tabIndex={menuOpen ? 0 : -1}>
              Registre-se
            </Link>
          </div>
        )}
      </div>

      {menuOpen && <div className={styles.backdrop} onClick={fecharMenu} aria-hidden="true" />}
    </header>
  );
}
