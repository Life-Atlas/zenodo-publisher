# zenodo-publisher — read before any deposit

The author's ORCID is `0009-0001-4011-8201`. Never `0000-0001-7970-2707` (an empty 2013 account with the same name). Every record in the Zenodo account must carry the right one; count them through the Zenodo API, not from this file.

Full rules, including how to correct metadata on a published record without a new version and how to publish a DOCX+PDF version through the REST API, are in `README.md` → "Before you publish: author identity and record hygiene". Read that section first.

After any SMILE publish (concept DOI `10.5281/zenodo.20175405`), run `node scripts/check-smile-version.mjs` in `C:\Users\ceo\winniio-site` and lift the site.
