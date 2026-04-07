"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useAuth } from "@/contexts/AuthContext";
import styles from "./Navbar.module.css";

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const isProfessorOuPesquisador =
    user?.papel === "professor" || user?.papel === "pesquisador";

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

  return (
    <header className={styles.header}>
      <nav className={styles.navbar}>
        <Link href="/" className={styles.logo}>
          <img src="/uniresulogo.png" alt="Logo Uniresu" className={styles.logoIcon} />
        </Link>

        <ul className={`${styles.navLinks} ${menuOpen ? styles.navOpen : ""}`}>
          <li><Link href="/" onClick={() => setMenuOpen(false)}>Home</Link></li>
          <li><Link href="/#quem-somos" onClick={() => setMenuOpen(false)}>Quem Somos</Link></li>
          <li><Link href="/projetos" onClick={() => setMenuOpen(false)}>Projetos Acadêmicos</Link></li>
          <li><Link href="/forum" onClick={() => setMenuOpen(false)}>Fórum</Link></li>
        </ul>

        <div className={styles.navActions}>
          {isAuthenticated ? (
            <div className={styles.userMenu}>
              {/* Avatar + Nome = abre dropdown */}
              <div className={styles.dropdownWrapper} ref={dropdownRef}>
                <button
                  className={styles.avatarButton}
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  aria-expanded={dropdownOpen}
                >
                  <div className={styles.avatar}>
                    {user?.nome?.charAt(0).toUpperCase() || "U"}
                  </div>
                  <span className={styles.userName}>
                    {user?.nome?.split(" ")[0]}
                  </span>
                  <span className={styles.dropdownArrow}>▾</span>
                </button>

                {dropdownOpen && (
                  <div className={styles.dropdownMenu}>
                    <Link
                      href="/perfil"
                      className={styles.dropdownItem}
                      onClick={() => setDropdownOpen(false)}
                    >
                      👤 Perfil
                    </Link>

                    {isProfessorOuPesquisador ? (
                      <Link
                        href="/projetos/gerenciar"
                        className={styles.dropdownItem}
                        onClick={() => setDropdownOpen(false)}
                      >
                        📋 Meus Projetos
                      </Link>
                    ) : (
                      <Link
                        href="/candidaturas"
                        className={styles.dropdownItem}
                        onClick={() => setDropdownOpen(false)}
                      >
                        📄 Candidaturas
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
                      🚪 Sair
                    </button>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className={styles.authButtons}>
              <Link href="/login" className={styles.btnLogin}>
                Entrar
              </Link>
              <Link href="/registrar" className={styles.btnRegister}>
                Registre-se
              </Link>
            </div>
          )}
        </div>

        <button
          className={styles.hamburger}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label="Abrir menu"
        >
          <span />
          <span />
          <span />
        </button>
      </nav>
    </header>
  );
}
