import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { rechercherDemandes } from "../api";
import type { Demande } from "../types";
import ListeDemandes, { formaterDate } from "./ListeDemandes";

function demande(id: number, demandeur: string, motif: string): Demande {
  return {
    id,
    demandeur,
    service: "Support",
    materiel: "Webcam",
    motif,
    statut: "en_attente",
    motif_refus: null,
    date_creation: "2026-11-20",
  };
}

describe("défauts de l'application de départ", () => {
  it("D4 : les détails ouverts suivent la demande, pas sa position", async () => {
    const a = demande(1, "Camille Martin", "Motif A");
    const b = demande(2, "Karim Benali", "Motif B");
    const c = demande(3, "Léa Fontaine", "Motif C");
    const { rerender } = render(<ListeDemandes demandes={[a, b, c]} />);
    await userEvent.click(screen.getAllByRole("button", { name: "Détails" })[1]);
    expect(screen.getByText(/Motif B/)).toBeInTheDocument();

    rerender(<ListeDemandes demandes={[a, c]} />);
    expect(screen.queryByText(/Motif C/)).not.toBeInTheDocument();
  });

  it("D5 : une réponse 503 n'est pas prise pour une liste", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 503, json: async () => ({ detail: "indisponible" }) })),
    );
    await expect(rechercherDemandes()).rejects.toThrow("503");
  });

  it("D3 : les dates ISO s'affichent au format français", () => {
    expect(formaterDate("2026-11-05")).toBe("05/11/2026");
  });
});
