import { useCallback, useEffect, useState } from "react";
import { listerDemandes } from "./api";
import FormulaireDemande from "./components/FormulaireDemande";
import ListeDemandes from "./components/ListeDemandes";
import type { Demande } from "./types";

export default function App() {
  const [demandes, setDemandes] = useState<Demande[]>([]);
  const [erreur, setErreur] = useState<string | null>(null);

  const charger = useCallback(() => {
    setErreur(null);
    listerDemandes()
      .then(setDemandes)
      .catch(() => setErreur("Impossible de charger les demandes."));
  }, []);

  useEffect(() => {
    charger();
  }, [charger]);

  return (
    <div className="page">
      <header className="entete">
        <h1>Portail interne</h1>
        <p>Demandes de matériel informatique</p>
      </header>
      <main>
        <FormulaireDemande onCreee={charger} />
        <section className="liste">
          <h2>Demandes</h2>
          {erreur && <p role="alert">{erreur}</p>}
          <ListeDemandes demandes={demandes} />
        </section>
      </main>
    </div>
  );
}
