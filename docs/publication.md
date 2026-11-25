# Marketplace submission candidate

Release: **0.1.0**, plugin ID `szaidi.scoring-matrix`, category **Hardware**, tags **bar, quickshell, system**. Update issue title: **[Verify]: Omarchy Hardware Score**.

## Prepared

- Root manifest and native QML entry point, with startup scanning disabled by default.
- MIT license, copyright 2026 szaidi-code, declared in the manifest and included by the terminal installer.
- HTTPS installation, update and removal instructions, dependencies, data storage and beta limitations.
- Local workload guidance, manually recorded compatibility checks, snapshot comparisons, an optional CPU microbenchmark, and a redacted export.
- Root `preview.png` shows the actual widget with the anonymous label “This computer”; README displays the same approved image.
- Release notes in [CHANGELOG.md](../CHANGELOG.md), runtime evidence in [qa.md](qa.md), and issue body in [submission.md](submission.md).
- Plugin ID listed in marketplace registry.

## Submission status

The initial submission [submission #5560](https://github.com/omacom/omarchy-plugin-marketplace/issues/5560) was approved and published. Upstream updates to name and assets use the verification workflow (`[Verify]: Omarchy Hardware Score`).

## Publication procedure

Publication and the privacy rewrite were authorized by the owner. Use the following procedure for any future resubmission.

1. Confirm the owner has rights to the code and preview and understands marketplace approval is for listing, not a security review.
2. Make `szaidi-code/scoring-matrix` public and update the repository description to: `Local hardware scores and evidence summaries for Omarchy. Native bar widget, optional startup scan, offline comparisons. MIT licensed.`
3. Confirm an unauthenticated clone works, CI is green, and the public default branch contains the intended candidate.
4. Review the release on physical hardware and record each target-device compatibility check. Do not represent the score as a compatibility certification.
5. Create a **Plugin verification** issue in `omacom/omarchy-plugin-marketplace` with action **Verify and publish a newer upstream commit**, the exact plugin ID and repository, and the full 40-character public `main` HEAD SHA. Obtain the owner's approval of the completed body before submission.
6. Record the issue URL and full reviewed commit SHA. Marketplace automation validates that exact commit; maintainer approval and `approved-and-verified` are still required before the marketplace update is published.

The initial listing request is retained in [submission.md](submission.md) for history; updates must use the current verification form.

Sources: [publishing guide](https://plugins.omarchy.org/publish.html), [submission procedure](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md), [verification form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=verify-plugin.yml).
