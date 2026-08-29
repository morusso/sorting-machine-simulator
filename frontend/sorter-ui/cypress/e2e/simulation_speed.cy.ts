describe("simulation speed control", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("shows the default x1 speed multiplier once connected", () => {
    cy.get("[data-cy=current-speed-multiplier]").should("have.text", "Sim speed: x1");
  });

  it("sets the speed multiplier via the x10 preset", () => {
    cy.get("[data-cy=speed-multiplier-x10]").click();
    cy.get("[data-cy=current-speed-multiplier]").should("have.text", "Sim speed: x10");
  });

  it("highlights the active preset", () => {
    cy.get("[data-cy=speed-multiplier-x2]").click();
    cy.get("[data-cy=current-speed-multiplier]").should("have.text", "Sim speed: x2");

    cy.get("[data-cy=speed-multiplier-x2]").should("have.class", "primary");
    cy.get("[data-cy=speed-multiplier-x1]").should("not.have.class", "primary");
  });
});
