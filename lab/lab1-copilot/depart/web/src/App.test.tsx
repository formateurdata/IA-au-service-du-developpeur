import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import App from "./App";
import type { Demande } from "./types";

const DEMANDES: Demande[] = [
  {
    id: 2,
    demandeur: "Karim Benali",
    service: "Support",
    materiel: "Casque audio",
    motif: "Casque actuel cassé.",
    statut: "validee",
    motif_refus: null,
    date_creation: "20/11/2026",
  },
  {
    id: 1,
    demandeur: "Camille Martin",
    service: "Développement",
    materiel: "Écran 27 pouces",
    motif: "Revue de code en binôme.",
    statut: "en_attente",
    motif_refus: null,
    date_creation: "21/11/2026",
  },
];

describe("App", () => {
  it("affiche les demandes renvoyées par l'API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: true, status: 200, json: async () => DEMANDES })),
    );
    render(<App />);
    expect(await screen.findByText("Karim Benali")).toBeInTheDocument();
    const tableau = screen.getByRole("table");
    expect(within(tableau).getByText("Camille Martin")).toBeInTheDocument();
    expect(within(tableau).getByText("Validée")).toBeInTheDocument();
  });

  it("propose le formulaire de nouvelle demande", () => {
    vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, status: 200, json: async () => [] })));
    render(<App />);
    expect(screen.getByRole("button", { name: "Envoyer la demande" })).toBeInTheDocument();
  });
});
