import { useEffect, useState } from "react";
import { rechercherDemandes } from "../api";
import { LIBELLES_STATUT, type Demande, type Statut } from "../types";
import ListeDemandes from "./ListeDemandes";

export const DELAI_ANTI_REBOND_MS = 300;

type Etat = { type: "chargement" } | { type: "erreur" } | { type: "pret"; demandes: Demande[] };

/**
 * Recherche et filtre des demandes. `version` change quand une demande est créée,
 * pour relancer la recherche en cours.
 */
export default function RechercheDemandes({ version = 0 }: { version?: number }) {
  const [saisie, setSaisie] = useState("");
  const [terme, setTerme] = useState("");
  const [statut, setStatut] = useState<Statut | "">("");
  const [essai, setEssai] = useState(0);
  const [etat, setEtat] = useState<Etat>({ type: "chargement" });

  // Anti-rebond : le terme recherché ne suit la saisie qu'après une pause.
  useEffect(() => {
    const minuteur = setTimeout(() => setTerme(saisie.trim()), DELAI_ANTI_REBOND_MS);
    return () => clearTimeout(minuteur);
  }, [saisie]);

  // Une requête par combinaison terme et statut ; la précédente est annulée.
  useEffect(() => {
    const controleur = new AbortController();
    setEtat({ type: "chargement" });
    rechercherDemandes({ q: terme, statut }, controleur.signal)
      .then((demandes) => {
        if (!controleur.signal.aborted) setEtat({ type: "pret", demandes });
      })
      .catch(() => {
        if (!controleur.signal.aborted) setEtat({ type: "erreur" });
      });
    return () => controleur.abort();
  }, [terme, statut, essai, version]);

  return (
    <div className="recherche">
      <div className="criteres">
        <label>
          Rechercher
          <input
            type="search"
            value={saisie}
            onChange={(e) => setSaisie(e.target.value)}
            placeholder="Nom ou matériel"
          />
        </label>
        <label>
          Statut
          <select value={statut} onChange={(e) => setStatut(e.target.value as Statut | "")}>
            <option value="">Tous</option>
            {(Object.keys(LIBELLES_STATUT) as Statut[]).map((s) => (
              <option key={s} value={s}>
                {LIBELLES_STATUT[s]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {etat.type === "chargement" && <p role="status">Chargement…</p>}
      {etat.type === "erreur" && (
        <div role="alert">
          La recherche a échoué.{" "}
          <button type="button" onClick={() => setEssai((n) => n + 1)}>
            Réessayer
          </button>
        </div>
      )}
      {etat.type === "pret" && etat.demandes.length === 0 && (
        <p>Aucune demande ne correspond à votre recherche.</p>
      )}
      {etat.type === "pret" && etat.demandes.length > 0 && <ListeDemandes demandes={etat.demandes} />}
    </div>
  );
}
