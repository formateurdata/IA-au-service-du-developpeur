import { useState } from "react";
import FormulaireDemande from "./components/FormulaireDemande";
import RechercheDemandes from "./components/RechercheDemandes";
import Assistant from "./pages/Assistant";

type Onglet = "demandes" | "assistant";

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
          <button type="button" aria-current={onglet === "assistant" ? "page" : undefined} onClick={() => setOnglet("assistant")}>
            Assistant procédures
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
          <Assistant />
        )}
      </main>
    </div>
  );
}
