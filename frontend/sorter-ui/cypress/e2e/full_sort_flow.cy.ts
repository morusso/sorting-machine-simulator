describe("full package sorting flow", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("carries a package from creation through scanning to a sorted, reclosed gate", () => {
    // "5901234567890" routes to gate 1 (see DEFAULT_ROUTING_TABLE in
    // app/simulation/sorting_line.py).
    cy.get("[data-cy=demo-barcode-5901234567890]").click();
    cy.get("[data-cy=package-status]").first().should("have.text", "IN_TRANSIT");

    cy.get("[data-cy=start-button]").click();

    cy.get("[data-cy=package-status]", { timeout: 5000 }).first().should("have.text", "ASSIGNED");
    cy.get("[data-cy=gate-1-state]", { timeout: 6000 }).should("have.text", "OPEN");
    cy.get("[data-cy=package-status]", { timeout: 4000 }).first().should("have.text", "SORTED");
    cy.get("[data-cy=gate-1-state]", { timeout: 3000 }).should("have.text", "CLOSED");

    cy.get("[data-cy=stat-sorted]").should("have.text", "1");
    cy.get("[data-cy=stat-total]").should("have.text", "1");
  });

  it("rejects a package whose barcode has no routing entry", () => {
    cy.get("[data-cy=barcode-input]").type("0000000000000");
    cy.get("[data-cy=create-package-button]").click();
    cy.get("[data-cy=start-button]").click();

    cy.get("[data-cy=package-status]", { timeout: 5000 }).first().should("have.text", "REJECTED");
    cy.get("[data-cy=stat-rejected]").should("have.text", "1");
    cy.get("[data-cy=gate-1-state]").should("have.text", "CLOSED");
    cy.get("[data-cy=gate-2-state]").should("have.text", "CLOSED");
    cy.get("[data-cy=gate-3-state]").should("have.text", "CLOSED");
  });
});
