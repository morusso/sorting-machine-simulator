import { defineConfig } from "cypress";

export default defineConfig({
  e2e: {
    baseUrl: "http://localhost:3000",
    supportFile: "cypress/support/e2e.ts",
    specPattern: "cypress/e2e/**/*.cy.ts",
    defaultCommandTimeout: 10000,
  },
  env: {
    apiUrl: "http://localhost:8000",
  },
});
