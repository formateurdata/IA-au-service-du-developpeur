export type Statut = "en_attente" | "validee" | "refusee" | "livree";

export interface NouvelleDemande {
  demandeur: string;
  service: string;
  materiel: string;
  motif: string;
}

export interface Demande extends NouvelleDemande {
  id: number;
  statut: Statut;
  motif_refus: string | null;
  date_creation: string;
}

export const LIBELLES_STATUT: Record<Statut, string> = {
  en_attente: "En attente",
  validee: "Validée",
  refusee: "Refusée",
  livree: "Livrée",
};
