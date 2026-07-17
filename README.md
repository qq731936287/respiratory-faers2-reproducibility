# Respiratory FAERS2 — public reproducibility archive

Status: sanitized public release (2026-07-16). Release `v0.1.1` is archived in Zenodo at [https://doi.org/10.5281/zenodo.21404580](https://doi.org/10.5281/zenodo.21404580).

This release contains reviewed analysis scripts, aggregate result tables, a reviewed PDF figure set, and an optional Streamlit evidence viewer. It intentionally does not redistribute report-level FAERS records, identifiers, dates, free-text fields, drug/indication/reaction/outcome rows, patient-level predictions, raw databases, model objects, author forms, or private configuration.

The included figures and aggregate tables are a reproducibility snapshot from the working analysis and are not a substitute for the journal's final revised figure/table files. Reconcile them with the final manuscript before citing a specific figure/table version.

## Data access

The FDA Adverse Event Reporting System (FAERS) / FDA Adverse Event Monitoring System (AEMS) quarterly data must be obtained by each user from the official FDA portal:

- https://www.fda.gov/drugs/fdas-adverse-event-reporting-system-faers/fda-adverse-event-reporting-system-faers-latest-quarterly-data-files
- https://www.fda.gov/drugs/drug-approvals-and-databases/fda-adverse-event-reporting-system-faers-database

The released tables are aggregate summaries derived from a local analysis run. They are not a substitute for the source data and should not be interpreted as causal estimates or individual clinical decision support.

## Included content

- R scripts in R/ for the refreshed cohort, feature engineering, model training, SHAP calculation, and figure generation.
- Aggregate tables in release_results/.
- Reviewed vector PDF figures in figures/.
- An optional dashboard in dashboard/ that reads only the included aggregate openFDA audit table and local structure catalog.

## Re-running the workflow

1. Install the documented R packages in docs/software_environment.md.
2. Obtain and prepare the required local FDA/easyFAERS input files. Raw inputs are not included here.
3. Set FAERS_INPUT_DIR to the local input directory before running R/31_refresh_easyfaers_2025Q2_Q4.R.
4. Run the scripts in numerical order from the repository root. The scripts write local data/results outputs that are intentionally ignored by version control.
5. Recreate figures only after verifying that the derived tables match the aggregate release tables.

The dashboard smoke test can be run without raw data:

    python dashboard/smoke_test.py

The easyFAERS helper package and any private data-preparation resources are not bundled in this release. The repository does not claim fully standalone reproducibility without a public, licensed installation route for that dependency.

## Dashboard

From the repository root:

    python -m pip install streamlit pandas
    streamlit run dashboard/app.py --server.port 8507

The dashboard is a convenience viewer for aggregate evidence and public openFDA links. It does not ship patient-level data.

## Provenance and limitations

- The analysis uses spontaneous reports and is descriptive/prognostic; it does not establish drug causality or incidence.
- The official FAERS/AEMS source is a time-varying quarterly snapshot. Record the exact download date and input release when reproducing.
- MedDRA release handling and the local easyFAERS preprocessing must be documented for each run.
- The repository metadata list the six-author working revision supplied for this release. Journal-required authorship confirmation remains separate from the code deposit.

## License and citation

LICENSE remains a placeholder pending author approval and does not grant reuse rights. Cite the archived release using [https://doi.org/10.5281/zenodo.21404580](https://doi.org/10.5281/zenodo.21404580).
