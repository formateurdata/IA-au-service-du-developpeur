import { LIBELLES_STATUT, type Statut } from "../types";

export default function BadgeStatut({ statut }: { statut: Statut }) {
  return <span className={`badge badge-${statut}`}>{LIBELLES_STATUT[statut]}</span>;
}
