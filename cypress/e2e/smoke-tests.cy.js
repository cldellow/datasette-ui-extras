/// <reference types="cypress" />

describe('dux smoke tests', () => {
  it('can click Edit and make a change on a simple row', () => {
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

  it('can render the Add row screen', () => {
    cy.visit('http://localhost:8888/diy/posts/dux-insert')
  })

  it('can render year facets', () => {
    cy.visit('http://localhost:8888/diy/posts?_facet_year=creation_date')
    cy.contains('creation_date (year)')
  })

  it('can render year-month facets', () => {
    cy.visit('http://localhost:8888/diy/posts?_facet_year_month=creation_date')
    cy.contains('creation_date (year_month)')
  })

  it('can render stats facets', () => {
    cy.visit('http://localhost:8888/diy/posts?_facet_stats=views')
    cy.contains('p99')
  })

  it('can render array facets', () => {
    cy.visit('http://localhost:8888/diy/posts?_facet_array=tags')
    cy.contains('tags (array)')
  })

  it('can filter by fkey and show label', () => {
    cy.visit('http://localhost:8888/diy/posts?_sort=id&owner_user_id__exact=17')
    cy.contains('where owner_user_id = 17 (Jeremy McGee)')
  })


})
