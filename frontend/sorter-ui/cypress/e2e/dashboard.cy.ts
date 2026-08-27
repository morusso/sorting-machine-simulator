describe("dashboard", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("connects to the backend and shows the initial machine state", () => {
    cy.get("[data-cy=connection-status]").should("contain.text", "connected");
    cy.get("[data-cy=engine-status]").should("contain.text", "STOPPED");

    cy.get("[data-cy=gate-card]").should("have.length", 3);
    cy.get("[data-cy=gate-1-state]").should("have.text", "CLOSED");
    cy.get("[data-cy=gate-2-state]").should("have.text", "CLOSED");
    cy.get("[data-cy=gate-3-state]").should("have.text", "CLOSED");

    cy.get("[data-cy=stat-total]").should("have.text", "0");
    cy.get("[data-cy=packages-panel]").should("contain.text", "No packages on the line yet.");
  });

  it("reflects backend state that existed before the page was even loaded", () => {
    cy.request("POST", `${Cypress.env("apiUrl")}/api/packages`, { barcode: "5901234567890" });
    cy.visit("/");

    cy.get("[data-cy=stat-total]").should("have.text", "1");
    cy.get("[data-cy=package-row]").should("have.length", 1);
  });
});
