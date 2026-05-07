import type { ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Layout({ children }: { children: ReactNode }) {
  const { session, signOut } = useAuth();
  const navigate = useNavigate();

  const onLogout = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  return (
    <div className="layout">
      <header className="layout__header">
        <Link to="/dashboard" className="layout__brand">
          Serverless Dashboard
        </Link>
        <nav className="layout__nav">
          {session ? (
            <button type="button" className="button button--secondary" onClick={onLogout}>
              Sair
            </button>
          ) : (
            <>
              <Link to="/login">Entrar</Link>
              <Link to="/register">Criar conta</Link>
            </>
          )}
        </nav>
      </header>
      <main className="layout__main">{children}</main>
    </div>
  );
}
