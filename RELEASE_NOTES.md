# Public release notes (v0.1.1)

This GitHub repository is a sanitized reproducibility candidate, not a redistribution of the underlying FAERS/AEMS report-level data. The repository intentionally excludes raw/report-level records, identifiers, dates, free text, patient-level predictions, model objects, author forms, and credentials.

This patch release also fixes the optional dashboard and smoke test so they resolve only the aggregate files shipped under `release_results/`; no private working-project paths are required.

Before an archived DOI is minted, the authors should:

- rotate the database credential found in the private source project;
- confirm the six-author list, contribution statement, and an approved code license;
- document a public installation route for the local easyFAERS dependency or state that the workflow is not standalone;
- reconcile the final manuscript figures and supplementary tables with the aggregate snapshot here;
- authorize Zenodo and verify that the resulting DOI resolves to this repository release.

Until those steps are complete, cite the GitHub repository URL rather than a DOI.
