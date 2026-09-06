declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Cypress {
    interface Chainable {
      /** Resets the live backend simulation to a fresh, empty state. */
      resetSimulation(): Chainable<Cypress.Response<unknown>>;
      /**
       * Creates a package directly via the API. Package creation is no
       * longer driven from a plain UI form (see OrderBarcodePicker, which
       * requires a barcode pre-registered on an order) — tests that only
       * need *some* package on the line to exercise unrelated behavior
       * (simulation lifecycle, gravity segment, sort flow) use this
       * instead of seeding an order through the orders service.
       */
      createPackage(barcode: string): Chainable<Cypress.Response<unknown>>;
    }
  }
}

Cypress.Commands.add("resetSimulation", () => {
  return cy.request("POST", `${Cypress.env("apiUrl")}/api/simulation/reset`);
});

Cypress.Commands.add("createPackage", (barcode: string) => {
  return cy.request("POST", `${Cypress.env("apiUrl")}/api/packages`, { barcode });
});

export {};
