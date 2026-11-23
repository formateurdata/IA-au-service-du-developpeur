import type { Demande, NouvelleDemande, Statut } from "./types";

export interface Criteres {
  q?: string;
  statut?: Statut | "";
}

/** Interroge GET /api/demandes ; lève une erreur si l'API ne répond pas 2xx. */
export async function rechercherDemandes(criteres: Criteres = {}, signal?: AbortSignal): Promise<Demande[]> {
  const parametres = new URLSearchParams();
  if (criteres.q) parametres.set("q", criteres.q);
  if (criteres.statut) parametres.set("statut", criteres.statut);
  const suite = parametres.toString();
  const reponse = await fetch(`/api/demandes${suite ? `?${suite}` : ""}`, { signal });
  if (!reponse.ok) {
    throw new Error(`Recherche impossible (${reponse.status})`);
  }
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

export interface ResultatCarte {
  html: string;
  controles: Record<string, boolean>;
  tokens_entree: number;
  tokens_sortie: number;
  cout_usd?: number;
}

/** Message lisible à partir d'une réponse d'erreur de l'API. */
async function messageErreur(reponse: Response, parDefaut: string): Promise<string> {
  try {
    const corps = await reponse.json();
    return typeof corps.detail === "string" ? corps.detail : parDefaut;
  } catch {
    return parDefaut;
  }
}

export async function genererCarte(description: string, mode: "libre" | "structure"): Promise<ResultatCarte> {
  const reponse = await fetch("/api/cartes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description, mode }),
  });
  if (!reponse.ok) {
    throw new Error(await messageErreur(reponse, `Génération impossible (${reponse.status})`));
  }
  return reponse.json();
}
