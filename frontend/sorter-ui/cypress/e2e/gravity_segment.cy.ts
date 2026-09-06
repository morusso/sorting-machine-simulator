describe("gravity segment buffer", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("hands a package off to the gravity buffer once it clears the driven segment", () => {
    // An unroutable barcode means the package is never removed by a gate,
    // so it rides the driven segment all the way to its end (20m at the
    // default 1.0 m/s belt speed — this genuinely takes ~20s).
    cy.createPackage("0000000000000");
    cy.get("[data-cy=start-button]").click();

    cy.get("[data-cy=package-status]", { timeout: 5000 }).first().should("have.text", "REJECTED");
    cy.get("[data-cy=gravity-segment-panel]").should("contain.text", "Gravity Buffer (0)");

    cy.get("[data-cy=gravity-package-dot]", { timeout: 25000 }).should("exist");
    cy.get("[data-cy=gravity-segment-panel]").should("contain.text", "Gravity Buffer (1)");
  });
});
