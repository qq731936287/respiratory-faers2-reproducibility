# R pipeline notes

The scripts are ordered as follows:

1. 31_refresh_easyfaers_2025Q2_Q4.R — optional local refresh of the 2025Q2–2025Q4 input slice.
2. 32_build_refreshed_dataset_2025Q4.R — builds report-level intermediate objects locally.
3. 33_feature_engineering_2025Q4.R — performs training-only feature selection.
4. 34_train_models_2025Q4.R — trains and evaluates the models.
5. 35_shap_2025Q4.R — calculates TreeSHAP summaries.
6. 36_make_publication_figures_2025Q4.R — generates figures from local analysis outputs.

Set FAERS_INPUT_DIR before step 1. The source files, report-level intermediates, model objects, and predictions are deliberately not distributed in this repository.

The 31 script calls locate_FAERS() and BFun() from easyFAERS. That helper is not bundled here; users must verify its provenance, license, and installation route independently before use. Do not put database credentials or local absolute paths into these scripts.

