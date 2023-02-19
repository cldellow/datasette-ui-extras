/// <reference types="cypress" />

describe('dux smoke tests', () => {
  it('can click Edit', () => {
    cy.visit('http://localhost:8888/diy/badges/6')
    cy.contains('Edit row').click();
    cy.url().should('include', '_dux_edit=1');
    cy.get('.col-name input').focus().type('{selectAll}s');

    // Confirm we see a dropdown result
    cy.contains('Scholar');

    // Write a new value
    cy.get('.col-name input').focus().type('{selectAll}xyzzy');
    cy.contains('Save').click();
  })
})
