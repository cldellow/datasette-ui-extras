---
title: Authentication, authorization and auditing
description: Learn how to secure your Datasette installation.
---

## Authentication

We rely on Datasette's built-in "actor" mechanism for authentication.

By default, every user is unauthenticated. You can change that by
installing a plugin that provides an authentication framework.

The most popular such plugin is [datasette-auth-github](https://github.com/simonw/datasette-auth-github/). This plugin permits people to sign in with their GitHub account. You can then distinguish users based on their GitHub user ID, org membership and team membership.

You can [learn more about actors here](https://docs.datasette.io/en/stable/authentication.html).

## Authorization

We rely on Datasette's built-in "permission" mechanism for authorization.

You can customize the behaviour by authoring a [`permission_allowed`](https://docs.datasette.io/en/stable/plugin_hooks.html#permission-allowed-datasette-actor-action-resource) hook.

You can [learn more about the default permissions here](https://docs.datasette.io/en/stable/authentication.html#built-in-permissions).

## Auditing

We use Datasette's Write API to make changes to your database. The Write API does not have an auditing feature.

If you'd like to track who is making what changes to your system, you can use SQLite's [TRIGGER feature](https://www.sqlite.org/lang_createtrigger.html#description) combined with the [datasette-current-actor plugin](https://github.com/cldellow/datasette-current-actor).

For example, you might make a trigger that records the value of `current_actor_ip()` and `current_actor('gh_id')` to know the IP address and GitHub user ID of the person changing the row.
