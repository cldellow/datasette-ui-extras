/// <reference types="cypress" />

describe('dux smoke tests', () => {
  it('displays two todo items by default', () => {
    cy.visit('http://localhost:8001/cooking/badges/6')
    cy.get('Edit row').should('have.length', 2)
  })
})
