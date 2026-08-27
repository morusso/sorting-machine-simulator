declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Cypress {
    interface Chainable {
      /** Resets the live backend simulation to a fresh, empty state. */
      resetSimulation(): Chainable<Cypress.Response<unknown>>;
    }
  }
}

Cypress.Commands.add("resetSimulation", () => {
  return cy.request("POST", `${Cypress.env("apiUrl")}/api/simulation/reset`);
});

export {};
