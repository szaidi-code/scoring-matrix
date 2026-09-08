# Marketplace submission candidate

Release: **0.1.0-beta.2**, plugin ID `szaidi.scoring-matrix`, category **Hardware**, tags **bar, quickshell, system**. Proposed issue title: **[Plugin]: Scoring Matrix**.

## Prepared

- Root manifest and native QML entry point, with startup scanning disabled by default.
- MIT license, copyright 2026 szaidi-code, declared in the manifest and included by the terminal installer.
- HTTPS installation, update and removal instructions, dependencies, data storage and beta limitations.
- Root preview captured from the running widget; no desktop wallpaper or unrelated windows in the asset.
- Release notes in [CHANGELOG.md](../CHANGELOG.md), runtime evidence in [qa.md](qa.md), and issue body in [submission.md](submission.md).
- Plugin ID absent from the marketplace registry checked September 7, 2026.

## Final publication steps

The GitHub repository was confirmed private on September 7, 2026. Making it public exposes its existing commit history as well as current files. Obtain the owner's final publication instruction before changing visibility or sending the submission issue.

1. Confirm the owner has rights to the code and preview and understands marketplace approval is for listing, not a security review.
2. Make `szaidi-code/scoring-matrix` public and update the repository description to: `Local hardware scores and evidence summaries for Omarchy. Native bar widget, optional startup scan, offline comparisons. MIT licensed.`
3. Confirm an unauthenticated clone works, CI is green, and the public default branch contains the intended candidate.
4. Check the remaining boxes in [submission.md](submission.md) once their statements are true, then create the issue with the proposed title in `omacom/omarchy-plugin-marketplace`.
5. Record the issue URL and full reviewed commit SHA. Marketplace automation validates the current public commit; maintainer approval is still required. Updates use the verification workflow for an exact upstream commit.

Sources: [publishing guide](https://plugins.omarchy.org/publish.html), [submission procedure](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md), [submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml).
