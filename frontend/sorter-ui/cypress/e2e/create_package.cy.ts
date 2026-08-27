describe("creating packages", () => {
  beforeEach(() => {
    cy.resetSimulation();
    cy.visit("/");
  });

  it("creates a package by typing a barcode", () => {
    cy.get("[data-cy=barcode-input]").type("5901234567890");
    cy.get("[data-cy=create-package-button]").click();

    cy.get("[data-cy=package-row]").should("have.length", 1);
    cy.get("[data-cy=package-row]").first().should("contain.text", "PKG-000001");
    cy.get("[data-cy=package-status]").first().should("have.text", "IN_TRANSIT");
    cy.get("[data-cy=stat-total]").should("have.text", "1");

    cy.get("[data-cy=barcode-input]").should("have.value", "");
  });

  it("creates a package via a quick demo-barcode shortcut", () => {
    cy.get("[data-cy=demo-barcode-5900000000000]").click();

    cy.get("[data-cy=package-row]").should("have.length", 1);
    cy.get("[data-cy=stat-total]").should("have.text", "1");
  });

  it("creates multiple packages with sequential ids", () => {
    cy.get("[data-cy=demo-barcode-5901234567890]").click();
    cy.get("[data-cy=demo-barcode-5900000000000]").click();

    cy.get("[data-cy=package-row]").should("have.length", 2);
    cy.get("[data-cy=stat-total]").should("have.text", "2");
    cy.contains("[data-cy=package-row]", "PKG-000001").should("exist");
    cy.contains("[data-cy=package-row]", "PKG-000002").should("exist");
  });

  it("disables the create button until a barcode is entered", () => {
    cy.get("[data-cy=create-package-button]").should("be.disabled");
    cy.get("[data-cy=barcode-input]").type("123");
    cy.get("[data-cy=create-package-button]").should("not.be.disabled");
  });
});
