import { useState } from "react";
import type { Demande } from "../types";
import BadgeStatut from "./BadgeStatut";

const FORMAT_DATE = new Intl.DateTimeFormat("fr-FR", { timeZone: "UTC" });

/** AAAA-MM-JJ vers JJ/MM/AAAA, pour l'affichage seulement. */
export function formaterDate(dateIso: string): string {
  const date = new Date(`${dateIso}T00:00:00Z`);
  return Number.isNaN(date.getTime()) ? dateIso : FORMAT_DATE.format(date);
}

export default function ListeDemandes({ demandes }: { demandes: Demande[] }) {
  return (
    <table className="demandes">
      <thead>
        <tr>
          <th scope="col">N°</th>
          <th scope="col">Demandeur</th>
          <th scope="col">Matériel</th>
          <th scope="col">Statut</th>
          <th scope="col">Date</th>
          <th scope="col">
            <span className="visuellement-cache">Détails</span>
          </th>
        </tr>
      </thead>
      <tbody>
        {demandes.map((demande) => (
          <LigneDemande key={demande.id} demande={demande} />
        ))}
      </tbody>
    </table>
  );
}

function LigneDemande({ demande }: { demande: Demande }) {
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
