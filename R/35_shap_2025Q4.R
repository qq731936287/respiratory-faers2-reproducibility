#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(xgboost)
})

set.seed(42)

project_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
data_dir <- file.path(project_root, "data")
table_dir <- file.path(project_root, "Table")
results_dir <- file.path(project_root, "results", "model_2025Q4")
log_dir <- file.path(project_root, "logs")
dir.create(table_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(results_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

log_file <- file.path(log_dir, "35_shap_2025Q4.log")
sink(log_file, split = TRUE)
on.exit(sink(), add = TRUE)

cat("============================================\n")
cat("35_shap_2025Q4\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("============================================\n\n")

load(file.path(data_dir, "ml_ready_2025Q4.RData"))
label_map <- readRDS(file.path(data_dir, "label_map_2025Q4.rds"))
xgb_model <- xgb.load(file.path(data_dir, "model_xgb_2025Q4.json"))

cat("Computing TreeSHAP on full held-out test set...\n")
cat("Test rows:", nrow(X_test), "Features:", ncol(X_test), "\n")
dtest <- xgb.DMatrix(X_test, label = y_test)
shap_raw <- predict(xgb_model, dtest, predcontrib = TRUE)
shap_raw <- as.matrix(shap_raw)
if (is.null(colnames(shap_raw))) {
  colnames(shap_raw) <- c(colnames(X_test), "BIAS")
}
bias_col <- if ("BIAS" %in% colnames(shap_raw)) {
  "BIAS"
} else {
  tail(colnames(shap_raw), 1)
}
shap_mat <- as.matrix(shap_raw[, setdiff(colnames(shap_raw), bias_col), drop = FALSE])
shap_bias <- shap_raw[, bias_col]

feature_category <- c(
  age_years = "Demographics",
  age_missing = "Demographics",
  sex_female = "Demographics",
  sex_male = "Demographics",
  has_resp_failure = "Respiratory AE",
  has_ild = "Respiratory AE",
  has_dyspnoea = "Respiratory AE",
  n_resp_pts = "Respiratory AE",
  has_cardiac_ae = "Co-morbid AE",
  has_renal_ae = "Co-morbid AE",
  has_hepatic_ae = "Co-morbid AE",
  has_pe = "Co-morbid AE",
  has_iv_route = "Clinical/Temporal",
  has_oral_route = "Clinical/Temporal",
  report_year = "Clinical/Temporal",
  tto_days = "Clinical/Temporal",
  tto_available = "Clinical/Temporal",
  n_total_aes = "Clinical/Temporal",
  n_total_drugs = "Drug Count",
  n_concomitant_drugs = "Drug Count",
  drug_immune_checkpoint_inhibitor = "Drug Class",
  drug_tnf_inhibitor = "Drug Class",
  drug_other_biologic = "Drug Class",
  drug_antineoplastic = "Drug Class",
  drug_targeted_therapy = "Drug Class",
  drug_anticoagulant = "Drug Class",
  drug_pah_therapy = "Drug Class",
  drug_antifibrotic = "Drug Class",
  drug_inhaled_respiratory = "Drug Class",
  drug_cardiovascular = "Drug Class",
  drug_antidiabetic = "Drug Class",
  has_cancer_indi = "Indication",
  has_cvd_indi = "Indication",
  has_diabetes_indi = "Indication"
)

feature_labels <- ifelse(colnames(shap_mat) %in% names(label_map),
                         unname(label_map[colnames(shap_mat)]),
                         colnames(shap_mat))

shap_importance <- data.table(
  Feature = colnames(shap_mat),
  Label = feature_labels,
  Category = ifelse(colnames(shap_mat) %in% names(feature_category),
                    feature_category[colnames(shap_mat)], "Other"),
  Mean_SHAP = colMeans(shap_mat),
  Mean_Abs_SHAP = colMeans(abs(shap_mat)),
  Median_Abs_SHAP = apply(abs(shap_mat), 2, median),
  Positive_SHAP_Fraction = colMeans(shap_mat > 0),
  Missing_Feature_Value_Fraction = colMeans(is.na(X_test))
)
setorder(shap_importance, -Mean_Abs_SHAP)
shap_importance[, Rank := .I]
setcolorder(shap_importance, c("Rank", "Feature", "Label", "Category"))

cat("Top SHAP features:\n")
print(shap_importance[1:min(.N, 15)])

cat("\nPreparing plotting sample...\n")
n_plot <- min(20000L, nrow(X_test))
idx_death <- which(y_test == 1)
idx_non <- which(y_test == 0)
n_death <- min(length(idx_death), ceiling(n_plot * 0.35))
n_non <- n_plot - n_death
plot_idx <- c(sample(idx_death, n_death), sample(idx_non, n_non))
plot_idx <- sample(plot_idx)

top_features <- shap_importance[1:min(20, .N), Feature]
sample_long <- rbindlist(lapply(top_features, function(f) {
  vals <- as.numeric(X_test[plot_idx, f])
  nonmiss <- vals[!is.na(vals)]
  if (length(unique(nonmiss)) > 5) {
    q <- quantile(nonmiss, c(0.02, 0.98), na.rm = TRUE, names = FALSE)
    vals_scaled <- pmin(pmax(vals, q[1]), q[2])
  } else {
    vals_scaled <- vals
  }
  data.table(
    Row_ID = plot_idx,
    Outcome = ifelse(y_test[plot_idx] == 1, "Death", "Non-death"),
    Feature = f,
    Label = ifelse(f %in% names(label_map), label_map[f], f),
    Category = ifelse(f %in% names(feature_category), feature_category[f], "Other"),
    Feature_Value = vals,
    Feature_Value_Scaled = vals_scaled,
    SHAP = as.numeric(shap_mat[plot_idx, f])
  )
}))
sample_long[, Feature_Label := factor(Label, levels = rev(shap_importance[Feature %in% top_features, Label]))]

save(shap_mat, shap_bias, shap_importance, sample_long, plot_idx, final_features,
     label_map, feature_category,
     file = file.path(data_dir, "shap_data_2025Q4.RData"))
fwrite(shap_importance, file.path(data_dir, "shap_importance_2025Q4.csv"))
fwrite(shap_importance, file.path(table_dir, "shap_importance_2025Q4.csv"))
fwrite(shap_importance, file.path(results_dir, "shap_importance_2025Q4.csv"))
fwrite(sample_long, file.path(results_dir, "shap_sample_long_2025Q4.csv"))

cat("\nSaved SHAP artifacts.\n")
cat("Completed:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
