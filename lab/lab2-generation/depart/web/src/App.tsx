import { useState } from "react";
import FormulaireDemande from "./components/FormulaireDemande";
import RechercheDemandes from "./components/RechercheDemandes";
import CarteBienvenue from "./pages/CarteBienvenue";

type Onglet = "demandes" | "carte";

export default function App() {
  const [version, setVersion] = useState(0);
  const [onglet, setOnglet] = useState<Onglet>("demandes");

  return (
    <div className="page">
      <header className="entete">
        <h1>Portail interne</h1>
        <nav className="onglets" aria-label="Sections du portail">
          <button type="button" aria-current={onglet === "demandes" ? "page" : undefined} onClick={() => setOnglet("demandes")}>
            Demandes de matériel
          </button>
          <button type="button" aria-current={onglet === "carte" ? "page" : undefined} onClick={() => setOnglet("carte")}>
            Carte de bienvenue
          </button>
        </nav>
      </header>
      <main>
        {onglet === "demandes" ? (
          <>
            <FormulaireDemande onCreee={() => setVersion((v) => v + 1)} />
            <section className="liste">
              <h2>Demandes</h2>
              <RechercheDemandes version={version} />
            </section>
          </>
        ) : (
          <CarteBienvenue />
        )}
      </main>
    </div>
  );
}
