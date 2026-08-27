describe("conveyor speed control", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("shows the conveyor's default speed once connected", () => {
    cy.get("[data-cy=current-speed]").should("have.text", "Speed: 1.00 m/s");
  });

  it("ramps the belt to a new target speed once running", () => {
    cy.get("[data-cy=start-button]").click();
    cy.get("[data-cy=current-speed]").should("have.text", "Speed: 1.00 m/s");

    cy.get("[data-cy=speed-input]").clear().type("1.8");
    cy.get("[data-cy=set-speed-button]").click();

    // Acceleration is 0.5 m/s^2, so ramping from 1.0 to 1.8 m/s takes ~1.6s;
    // the background loop advances real time, so this genuinely takes a moment.
    cy.get("[data-cy=current-speed]", { timeout: 8000 }).should("have.text", "Speed: 1.80 m/s");
  });

  it("rejects a speed above the conveyor's max and surfaces the error", () => {
    cy.get("[data-cy=speed-input]").clear().type("99");
    cy.get("[data-cy=set-speed-button]").click();

    cy.get("[data-cy=error-banner]").should("be.visible");
  });
});
