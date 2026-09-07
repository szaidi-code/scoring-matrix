# Marketplace publication preparation

The candidate is still a private beta. Do not submit the draft below until repository visibility, license and ownership decisions are complete.

## Current readiness

- Root manifest, permanent ID `szaidi.scoring-matrix`, QML entry point, dependencies, install/update/removal instructions: present.
- Public repository: README identifies the project as private beta; visibility must be confirmed and changed by the owner before listing.
- Root license: missing. Choose an appropriate license and copyright holder before adding the file and manifest `license` field.
- Preview: `preview.png` captures the actual QA plugin, without unrelated application windows. It contains the QA computer label and provisional score; review the asset before public submission.
- Runtime QA: see `qa.md` for the tested candidate and limits.

The marketplace takes one public GitHub repository with a root manifest. It validates the submitted commit and runs a static security baseline. A maintainer must review and approve the exact candidate for listing. Follow-up updates use the plugin verification form and a full upstream commit SHA; a newer Git commit alone does not establish that the marketplace snapshot is updated.

Sources: [publishing guide](https://plugins.omarchy.org/publish.html), [submission procedure](https://github.com/omacom/omarchy-plugin-marketplace/blob/main/SUBMISSION.md), [submission form](https://github.com/omacom/omarchy-plugin-marketplace/issues/new?template=submit-plugin.yml).

## Draft title

`[Plugin]: Scoring Matrix`

## Draft body

### Repository URL

https://github.com/szaidi-code/scoring-matrix

### Category

Hardware

### Tags

bar, quickshell, system

### Suggest a missing tag

_No response_

### Maintainer notes

Local, on-demand hardware inventory and provisional readiness scores. No network access or automatic hardware scans. Uses Python 3.9+, util-linux; optional pciutils and usbutils improve inventory names. The bar widget runs inside the existing Omarchy shell; the separate application-menu installer is optional. Matrix 1.0 is a capacity and compatibility estimate, not a performance benchmark or certification. Reports remain local; no sudo is required.

### Submission checklist

- [ ] The repository is public and contains installation and removal instructions.
- [ ] I have documented the plugin license and any external dependencies.
- [ ] I confirm that I own or have permission to submit this plugin and its preview assets.
- [ ] The plugin does not overwrite user configuration without explicit consent.
- [ ] I understand that approval is for listing and is not a security review.

The unchecked draft is intentionally not submission-ready. The owner must confirm each statement, choose the license and approve the completed title/body before an issue is created.
