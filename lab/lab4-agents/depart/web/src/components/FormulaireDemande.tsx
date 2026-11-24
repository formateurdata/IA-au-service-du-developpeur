import { useState, type FormEvent } from "react";
import { creerDemande } from "../api";

const SERVICES = ["Data", "Design", "Développement", "Finance", "Infrastructure", "RH", "Support"];
const MATERIELS = [
  "Casque audio",
  "Clavier ergonomique",
  "Disque SSD externe",
  "Écran 27 pouces",
  "Ordinateur portable",
  "Second écran",
  "Souris verticale",
  "Station d'accueil",
  "Tablette graphique",
  "Téléphone mobile",
  "Webcam",
];

export default function FormulaireDemande({ onCreee }: { onCreee: () => void }) {
  const [demandeur, setDemandeur] = useState("");
  const [service, setService] = useState(SERVICES[0]);
  const [materiel, setMateriel] = useState(MATERIELS[0]);
  const [motif, setMotif] = useState("");
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  async function envoyer(evenement: FormEvent) {
    evenement.preventDefault();
    setEnvoi(true);
    setErreur(null);
    try {
      await creerDemande({ demandeur, service, materiel, motif });
      setDemandeur("");
      setMotif("");
      onCreee();
    } catch {
      setErreur("La demande n'a pas pu être enregistrée. Vérifiez les champs.");
    } finally {
      setEnvoi(false);
    }
  }

  return (
    <form className="formulaire" onSubmit={envoyer}>
      <h2>Nouvelle demande</h2>
      <label>
        Demandeur
        <input value={demandeur} onChange={(e) => setDemandeur(e.target.value)} required minLength={2} />
      </label>
      <label>
        Service
        <select value={service} onChange={(e) => setService(e.target.value)}>
          {SERVICES.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <label>
        Matériel
        <select value={materiel} onChange={(e) => setMateriel(e.target.value)}>
          {MATERIELS.map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </label>
      <label className="large">
        Motif
        <textarea value={motif} onChange={(e) => setMotif(e.target.value)} required minLength={5} rows={2} />
      </label>
      {erreur && <p role="alert">{erreur}</p>}
      <button type="submit" disabled={envoi}>
        {envoi ? "Envoi…" : "Envoyer la demande"}
      </button>
    </form>
  );
}
