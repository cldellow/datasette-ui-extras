# Docs

> **NOTE**
>
> MOST OF THIS FOLDER IS _NOT_ APACHE-2.0 LICENSED.
> SEE LICENSE.MD, WHICH GOVERNS EVERY NON .md FILE IN THIS
> FOLDER AND ITS SUBFOLDERS.

Syntax is a [Tailwind UI](https://tailwindui.com) site template built using [Tailwind CSS](https://tailwindcss.com) and [Next.js](https://nextjs.org).

## Editing documentation

```bash
yarn install
yarn dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to view the website.

## Global search

TODO: Can't apply for this until we have docs.

By default this template uses [Algolia DocSearch](https://docsearch.algolia.com) for the global search. DocSearch is free for open-source projects, and you can sign up for an account on their website. Once your DocSearch account is ready, update the following [environment variables](https://nextjs.org/docs/basic-features/environment-variables) in your project with the values provided by Algolia:

```
NEXT_PUBLIC_DOCSEARCH_APP_ID=
NEXT_PUBLIC_DOCSEARCH_API_KEY=
NEXT_PUBLIC_DOCSEARCH_INDEX_NAME=
```

## License

This site template is a commercial product and is licensed under the [Tailwind UI license](https://tailwindui.com/license).

The license is a bit confusing about how it can be used in open source. I believe this use is OK, see https://discord.com/channels/674983035946663957/1056206923835379773/1058138762091188345
for comments by Adam Wathan. Happy to hide the source if needed.
