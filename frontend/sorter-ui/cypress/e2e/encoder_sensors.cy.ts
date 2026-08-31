describe("encoder and sensors panel", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("shows the encoder and sensors with their initial idle state", () => {
    cy.get("[data-cy=encoder-sensor-panel]").should("be.visible");
    cy.get("[data-cy=encoder-pulse-count]").should("have.text", "Encoder: 0 pulses");
    cy.get("[data-cy=sensor-SENSOR-ENTRY]").should("contain.text", "IDLE");
    cy.get("[data-cy=sensor-SENSOR-END-OF-BELT]").should("contain.text", "IDLE");
  });

  it("increases the encoder pulse count as the belt moves", () => {
    cy.get("[data-cy=start-button]").click();

    // The background loop advances real time, so the pulse count only
    // climbs once a few ticks have actually run.
    cy.get("[data-cy=encoder-pulse-count]", { timeout: 8000 }).should(($el) => {
      const pulses = Number($el.text().replace(/[^\d]/g, ""));
      expect(pulses).to.be.greaterThan(0);
    });
  });
});
