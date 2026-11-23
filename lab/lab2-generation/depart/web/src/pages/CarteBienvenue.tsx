import { useState, type FormEvent } from "react";
import { genererCarte, type ResultatCarte } from "../api";

const EXEMPLE =
  "Carte de bienvenue pour Camille Martin, développeuse, qui rejoint l'équipe Data le 1er décembre. " +
  "Son référent est Karim Benali. Ajouter trois boutons : Écrire à Camille, Voir l'équipe, Planifier un café.";

export default function CarteBienvenue() {
  const [description, setDescription] = useState(EXEMPLE);
  const [mode, setMode] = useState<"libre" | "structure">("libre");
  const [resultat, setResultat] = useState<ResultatCarte | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  async function generer(evenement: FormEvent) {
    evenement.preventDefault();
    setEnCours(true);
    setErreur(null);
    try {
      setResultat(await genererCarte(description, mode));
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Génération impossible.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section className="panneau">
      <h2>Carte de bienvenue d'un nouvel arrivant</h2>
      <form className="generation" onSubmit={generer}>
        <label>
          Décrivez la carte
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} required minLength={10} />
        </label>
        <fieldset>
          <legend>Prompt</legend>
          <label className="choix">
            <input type="radio" name="mode" checked={mode === "libre"} onChange={() => setMode("libre")} />
            Libre : la description seule
          </label>
          <label className="choix">
            <input type="radio" name="mode" checked={mode === "structure"} onChange={() => setMode("structure")} />
            Structuré : prompt système et format imposé
          </label>
        </fieldset>
        <button type="submit" disabled={enCours}>
          {enCours ? "Génération…" : "Générer"}
        </button>
      </form>

      {erreur && <p role="alert">{erreur}</p>}

      {resultat && (
        <div className="resultat">
          <ul className="controles">
            {Object.entries(resultat.controles).map(([nom, tenu]) => (
              <li key={nom} className={tenu ? "tenu" : "non-tenu"}>
                {tenu ? "oui" : "NON"} · {nom}
              </li>
            ))}
          </ul>
          <p className="discret">
            {resultat.tokens_entree} tokens en entrée, {resultat.tokens_sortie} en sortie
            {resultat.cout_usd !== undefined && <>, {resultat.cout_usd.toFixed(5)} $</>}
          </p>
          <h3>Aperçu</h3>
          {/* Le HTML reçu est inséré tel quel dans la page du portail. */}
          <div className="apercu" dangerouslySetInnerHTML={{ __html: resultat.html }} />
          <details>
            <summary>Code reçu</summary>
            <pre>{resultat.html}</pre>
          </details>
        </div>
      )}
    </section>
  );
}
