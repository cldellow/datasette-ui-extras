---
title: Publish to the web
description: Learn how to safely publish a mutable Datasette to the web.
---

## Mutable state

Most Datasette releases are _immutable_. The techniques for deploying them
are not suitable for deploying a Datasette that is read-write.

We recommend Fly as a good hosting alternative. They have a generous
free tier and then pay-as-you pricing.

Simon Willison has documented [how to deploy a mutable database to Fly](https://simonwillison.net/2022/Feb/15/fly-volumes/) on his website.

## Backups

There is not currently a way to do automated cloud backups.

At the moment, I'd recommend using [datasette-backup](https://github.com/simonw/datasette-backup) and scheduling a cron job to periodically fetch your database and store it somewhere safe.
