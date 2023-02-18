---
title: Getting started
pageTitle: datasette-ui-extras - make Datasette even more awesome
description: Add power-user search features and an edit UI to Datasette.
---

`datasette-ui-extras` (dux) makes [Datasette](https://datasette.io/) even more awesome: it adds an edit UI and several power-user features for browsing your data. {% .lead %}

{% quick-links %}

{% quick-link title="Configuration" icon="installation" href="/docs/authn-authz-auditing" description="Learn how to configure and secure your installation." /%}

{% commented-quick-link title="Use case guides" icon="theming" href="/docs/data-entry" description="Learn how to implement common use cases, like data entry, turking and forms." /%}

{% quick-link title="Plugins" icon="plugins" href="/docs/hooks" description="Extend the library with third-party plugins or write your own." /%}

{% quick-link title="Architecture guide" icon="presets" href="/docs/architecture-guide" description="Learn how the internals work and contribute." /%}


{% /quick-links %}

---

## Installing


### Quick start

The fastest way to get a test environment is to run these commands in your shell:

```shell
pipx install datasette==1.0a2
datasette install datasette-ui-extras
datasette yolo data.db
datasette --metadata metadata.json data.db
```

This installs Datasette, specifying the as-yet-unreleased 1.0 version, which is necessary for its Write API.

Then it installs the `datasette-ui-extras` plugin.

It then creates an empty database called `data.db`, and configures your server to grant anyone full permissions to interact with and change this database.

Then it starts Datasette. You're ready to go!

{% callout type="warning" title="YOLO" %}
The `yolo` command grants _anyone_ access to your database. This is convenient and suitable for testing on your own laptop. It's _not_ appropriate for a Datasette instance that will be published to the web. For those, see the [Authentication, authorization and auditing](/docs/authn-authz-auditing) section.
{% /callout %}

### macOS, Windows and other platforms

`datasette-ui-extras` is a regular Datasette plugin. We've shown the "happy path" for installing on Linux. If you use a different platform, please see [the official Datasette docs](https://docs.datasette.io/en/stable/installation.html) for help.

## Getting help

`datasette-ui-extras` is still very new. There will likely be issues! Please let me know.

### Submit an issue

If `datasette-ui-extras` does something unexpected, or the documentation isn't clear, please open a GitHub issue.

You can open a new issue [here](https://github.com/cldellow/datasette-ui-extras/issues/new).

Please include as much information as you can about how to reproduce it, for example:

- your operating system
- your web browser
- the steps you were doing when it happened

Ideally, you'd be able to share the underlying SQLite database, too.

If you have the skills to propose or submit a fix, please feel free to do so! You can learn more in the [How to contribute](/docs/how-to-contribute) section.

### Join the community

If your question is more generally about Datasette itself, please use the [Datasette Discord](https://datasette.io/discord) to ask the community for help.
