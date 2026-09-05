describe("simulation lifecycle controls", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
    cy.get("[data-cy=engine-status]").should("contain.text", "STOPPED");
  });

  it("starts the simulation and updates button/status state", () => {
    cy.get("[data-cy=start-button]").should("not.be.disabled");
    cy.get("[data-cy=stop-button]").should("be.disabled");

    cy.get("[data-cy=start-button]").click();

    cy.get("[data-cy=engine-status]").should("contain.text", "RUNNING");
    cy.get("[data-cy=start-button]").should("be.disabled");
    cy.get("[data-cy=stop-button]").should("not.be.disabled");
  });

  it("pauses and resumes a running simulation", () => {
    cy.get("[data-cy=pause-button]").should("be.disabled");
    cy.get("[data-cy=resume-button]").should("be.disabled");

    cy.get("[data-cy=start-button]").click();
    cy.get("[data-cy=engine-status]").should("contain.text", "RUNNING");
    cy.get("[data-cy=pause-button]").should("not.be.disabled");
    cy.get("[data-cy=start-button]").should("be.disabled");

    cy.get("[data-cy=pause-button]").click();
    cy.get("[data-cy=engine-status]").should("contain.text", "PAUSED");
    cy.get("[data-cy=pause-button]").should("be.disabled");
    cy.get("[data-cy=resume-button]").should("not.be.disabled");
    cy.get("[data-cy=stop-button]").should("not.be.disabled");

    cy.get("[data-cy=resume-button]").click();
    cy.get("[data-cy=engine-status]").should("contain.text", "RUNNING");
    cy.get("[data-cy=resume-button]").should("be.disabled");
  });

  it("stops a paused simulation", () => {
    cy.get("[data-cy=start-button]").click();
    cy.get("[data-cy=pause-button]").click();
    cy.get("[data-cy=engine-status]").should("contain.text", "PAUSED");

    cy.get("[data-cy=stop-button]").click();

    cy.get("[data-cy=engine-status]").should("contain.text", "STOPPED");
    cy.get("[data-cy=start-button]").should("not.be.disabled");
  });

  it("stops a running simulation", () => {
    cy.get("[data-cy=start-button]").click();
    cy.get("[data-cy=engine-status]").should("contain.text", "RUNNING");

    cy.get("[data-cy=stop-button]").click();

    cy.get("[data-cy=engine-status]").should("contain.text", "STOPPED");
    cy.get("[data-cy=start-button]").should("not.be.disabled");
  });

  it("resets the simulation, clearing packages and statistics", () => {
    cy.createPackage("5901234567890");
    cy.get("[data-cy=stat-total]").should("have.text", "1");

    cy.get("[data-cy=start-button]").click();
    cy.get("[data-cy=reset-button]").click();

    cy.get("[data-cy=engine-status]").should("contain.text", "STOPPED");
    cy.get("[data-cy=stat-total]").should("have.text", "0");
    cy.get("[data-cy=packages-panel]").should("contain.text", "No packages on the line yet.");
  });
});
