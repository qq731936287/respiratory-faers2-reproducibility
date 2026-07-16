# Public release manifest

This is the sanitized public release assembled on 2026-07-16 and published at the GitHub repository. The repository is public and release `v0.1.1` contains the same reviewed snapshot after the dashboard path fix. A Zenodo DOI is not yet assigned.

## Included

- Six sanitized R scripts under R/.
- Four dashboard files under dashboard/.
- Eleven aggregate result tables under release_results/.
- Twelve reviewed PDF figures under figures/.
- README.md, R/README.md, docs/software_environment.md, this manifest, LICENSE, CITATION.cff, and .gitignore.

The figures and aggregate tables are a working-analysis snapshot and must be reconciled with the final revised manuscript before release.

## Excluded

Raw and report-level FAERS data, identifiers, dates, model objects, predictions, SHAP sample-long data, raw input tables, logs, private project-state files, manuscript/author documents, spreadsheets, AppleDouble metadata, compiled Python caches, credentials, and external symlinks are excluded.

## Scan gate

The staging files were screened for credential strings, email addresses, private absolute paths, report identifiers, and local configuration. The only known source-side path was removed from the copied refresh script and replaced by FAERS_INPUT_DIR. Aggregate openFDA query URLs are public endpoints and remain only in the included audit table. The PDF text scan found ordinary scientific labels but no author contact details or report identifiers.

The dashboard smoke test is designed to run from the repository root and reads only the aggregate files under `release_results/`. Before a future release, rerun a repository-wide secret/path scan, review the final author list and license, verify that the credential-bearing source files have not been staged, and obtain a real archive DOI if one is required.
