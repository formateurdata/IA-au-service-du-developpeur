import { useState, type FormEvent } from "react";
import { demanderAssistant, type ModeRecherche, type ReponseAssistant } from "../api";

const MODES: { valeur: ModeRecherche; libelle: string }[] = [
  { valeur: "aucun", libelle: "Sans document (le modèle seul)" },
  { valeur: "semantique", libelle: "Recherche sémantique" },
  { valeur: "lexicale", libelle: "Recherche lexicale" },
  { valeur: "hybride", libelle: "Recherche hybride" },
];

export default function Assistant() {
  const [question, setQuestion] = useState("");
  const [mode, setMode] = useState<ModeRecherche>("hybride");
  const [resultat, setResultat] = useState<ReponseAssistant | null>(null);
  const [erreur, setErreur] = useState<string | null>(null);
  const [enCours, setEnCours] = useState(false);

  async function demander(evenement: FormEvent) {
    evenement.preventDefault();
    setEnCours(true);
    setErreur(null);
    setResultat(null);
    try {
      setResultat(await demanderAssistant(question, mode));
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Question impossible.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <section className="panneau">
      <h2>Assistant procédures</h2>
      <p className="discret">Les réponses viennent des procédures internes : congés, télétravail, notes de frais, astreinte, matériel, accueil.</p>
      <form className="generation" onSubmit={demander}>
        <label>
          Votre question
          <input value={question} onChange={(e) => setQuestion(e.target.value)} required minLength={3} placeholder="Combien de jours de télétravail par semaine ?" />
        </label>
        <label>
          Recherche
          <select value={mode} onChange={(e) => setMode(e.target.value as ModeRecherche)}>
            {MODES.map((m) => (
              <option key={m.valeur} value={m.valeur}>
                {m.libelle}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={enCours}>
          {enCours ? "Recherche…" : "Demander"}
        </button>
      </form>

      {erreur && <p role="alert">{erreur}</p>}

      {resultat && (
        <div className="reponse" aria-live="polite">
          <p>{resultat.reponse}</p>
          <p className="discret">
            {/* Les documents transmis au modèle, pas la preuve que chacun a servi à la réponse. */}
            {resultat.sources.length > 0
              ? <>Documents consultés : {resultat.sources.join(", ")}</>
              : "Aucun document à l'appui de cette réponse."}
          </p>
        </div>
      )}
    </section>
  );
}
