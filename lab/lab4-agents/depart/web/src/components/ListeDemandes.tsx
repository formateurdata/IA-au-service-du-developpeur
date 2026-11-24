import type { Demande } from "../types";
import LigneDemande from "./LigneDemande";

// Le format des dates reste disponible ici, où les tests de la liste le lisent.
export { formaterDate } from "./LigneDemande";

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
