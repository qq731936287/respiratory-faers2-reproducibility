# Public release notes (v0.1.1)

This GitHub repository is a sanitized reproducibility archive, not a redistribution of the underlying FAERS/AEMS report-level data. The repository intentionally excludes raw/report-level records, identifiers, dates, free text, patient-level predictions, model objects, author forms, and credentials.

This patch release also fixes the optional dashboard and smoke test so they resolve only the aggregate files shipped under `release_results/`; no private working-project paths are required.

Release `v0.1.1` is archived in Zenodo at [https://doi.org/10.5281/zenodo.21404580](https://doi.org/10.5281/zenodo.21404580).

The following scope limitations and author-side actions remain:

- rotate the database credential found in the private source project;
- confirm the five-author list, contribution statement, and an approved code license;
- document a public installation route for the local easyFAERS dependency or state that the workflow is not standalone;
- reconcile the final manuscript figures and supplementary tables with the aggregate snapshot here;
- verify that future manuscript figure and supplementary-table revisions remain aligned with the archived aggregate snapshot.
