import type { Demande, NouvelleDemande } from "./types";

export async function listerDemandes(): Promise<Demande[]> {
  const reponse = await fetch("/api/demandes");
  return reponse.json();
}

export async function creerDemande(demande: NouvelleDemande): Promise<Demande> {
  const reponse = await fetch("/api/demandes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(demande),
  });
  if (!reponse.ok) {
    throw new Error(`Création impossible (${reponse.status})`);
  }
  return reponse.json();
}
