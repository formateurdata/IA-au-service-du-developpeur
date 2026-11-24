import { useState } from "react";
import type { Demande } from "../types";
import BadgeStatut from "./BadgeStatut";

const FORMAT_DATE = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC" });

/** AAAA-MM-JJ vers JJ/MM/AAAA, pour l'affichage seulement. */
export function formaterDate(dateIso: string): string {
  const date = new Date(`${dateIso}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? dateIso : FORMAT_DATE.format(date);
}

/** Une ligne du tableau des demandes, et ses détails à la demande. */
export default function LigneDemande({ demande }: { demande: Demande }) {
  const [ouverte, setOuverte] = useState(false);
  return (
    <>
      <tr>
        <td>{demande.id}</td>
        <td>{demande.demandeur}</td>
        <td>{demande.materiel}</td>
        <td>
          <BadgeStatut statut={demande.statut} />
        </td>
        <td>{formaterDate(demande.date_creation)}</td>
        <td>
          <button type="button" aria-expanded={ouverte} onClick={() => setOuverte(!ouverte)}>
            {ouverte ? "Masquer" : "Détails"}
          </button>
        </td>
      </tr>
      {ouverte && (
        <tr className="details">
          <td colSpan={6}>
            <strong>Service :</strong> {demande.service} · <strong>Motif :</strong> {demande.motif}
            {demande.motif_refus && (
              <>
                {" "}
                · <strong>Motif du refus :</strong> {demande.motif_refus}
              </>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
