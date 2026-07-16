#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(glmnet)
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

log_file <- file.path(log_dir, "33_feature_engineering_2025Q4.log")
sink(log_file, split = TRUE)
on.exit(sink(), add = TRUE)

cat("============================================\n")
cat("33_feature_engineering_2025Q4\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("============================================\n\n")

load(file.path(data_dir, "respiratory_ae_data_2025Q4.RData"))
ml <- copy(ml_data_2025Q4)
cat("Known-outcome ML data:", nrow(ml), "rows\n")
cat("Year range:", min(ml$report_year, na.rm = TRUE), "-", max(ml$report_year, na.rm = TRUE), "\n")
print(ml[, .N, by = .(report_year, report_quarter)][order(report_year, report_quarter)])

cat("\nDrug pharmacological classification...\n")
patterns <- list(
  drug_immune_checkpoint_inhibitor = "KEYTRUDA|PEMBROLIZUMAB|NIVOLUMAB|OPDIVO|ATEZOLIZUMAB|TECENTRIQ|DURVALUMAB|IMFINZI|AVELUMAB|BAVENCIO|IPILIMUMAB|YERVOY|CEMIPLIMAB|LIBTAYO|TREMELIMUMAB",
  drug_tnf_inhibitor = "HUMIRA|ADALIMUMAB|ENBREL|ETANERCEPT|REMICADE|INFLIXIMAB|INFLECTRA|SIMPONI|GOLIMUMAB|CIMZIA|CERTOLIZUMAB",
  drug_other_biologic = "RITUXIMAB|RITUXAN|ACTEMRA|TOCILIZUMAB|COSENTYX|SECUKINUMAB|DUPIXENT|DUPILUMAB|XELJANZ|TOFACITINIB|RINVOQ|UPADACITINIB|VEDOLIZUMAB|ENTYVIO|OCREVUS|OCRELIZUMAB|JAKAFI|RUXOLITINIB|BARICITINIB|OLUMIANT",
  drug_antineoplastic = "METHOTREXATE|REVLIMID|LENALIDOMIDE|IBRANCE|PALBOCICLIB|IMBRUVICA|IBRUTINIB|AFINITOR|EVEROLIMUS|POMALYST|POMALIDOMIDE|CYCLOPHOSPHAMIDE|DOCETAXEL|PACLITAXEL|CISPLATIN|CARBOPLATIN|GEMCITABINE|PEMETREXED|IRINOTECAN|FLUOROURACIL|CAPECITABINE|DOXORUBICIN",
  drug_targeted_therapy = "SORAFENIB|SUNITINIB|ERLOTINIB|GEFITINIB|CRIZOTINIB|ALECTINIB|OSIMERTINIB|TAGRISSO|IMATINIB|DASATINIB|NILOTINIB|BOSUTINIB|PONATINIB|CABOZANTINIB|LENVATINIB|REGORAFENIB|AXITINIB|PAZOPANIB|LAPATINIB|TRASTUZUMAB|HERCEPTIN|PERTUZUMAB|ADO-TRASTUZUMAB",
  drug_anticoagulant = "XARELTO|RIVAROXABAN|ELIQUIS|APIXABAN|PRADAXA|DABIGATRAN|EDOXABAN|WARFARIN|COUMADIN|HEPARIN|ENOXAPARIN|LOVENOX",
  drug_pah_therapy = "AMBRISENTAN|LETAIRIS|OPSUMIT|MACITENTAN|TRACLEER|BOSENTAN|REMODULIN|TREPROSTINIL|TYVASO|UPTRAVI|SELEXIPAG|ADEMPAS|RIOCIGUAT|FLOLAN|EPOPROSTENOL|VENTAVIS|ILOPROST|SILDENAFIL|REVATIO|TADALAFIL|ADCIRCA",
  drug_antifibrotic = "OFEV|NINTEDANIB|ESBRIET|PIRFENIDONE",
  drug_inhaled_respiratory = "SPIRIVA|TIOTROPIUM|SYMBICORT|BUDESONIDE|FORMOTEROL|ADVAIR|FLUTICASONE|SALMETEROL|SALBUTAMOL|ALBUTEROL|XOLAIR|OMALIZUMAB|MEPOLIZUMAB|NUCALA|BENRALIZUMAB|FASENRA|DUPIXENT|MONTELUKAST|SINGULAIR|IPRATROPIUM|BREO|UMECLIDINIUM|GLYCOPYRROLATE|TRELEGY",
  drug_cardiovascular = "ENTRESTO|SACUBITRIL|AMLODIPINE|METOPROLOL|ATENOLOL|CARVEDILOL|BISOPROLOL|LOSARTAN|VALSARTAN|IRBESARTAN|LISINOPRIL|RAMIPRIL|ENALAPRIL|DIGOXIN|AMIODARONE|FUROSEMIDE|SPIRONOLACTONE|HYDROCHLOROTHIAZIDE",
  drug_antidiabetic = "METFORMIN|INSULIN|EMPAGLIFLOZIN|JARDIANCE|DAPAGLIFLOZIN|CANAGLIFLOZIN|SITAGLIPTIN|LIRAGLIDE|LIRAGLUTIDE|SEMAGLUTIDE|GLIPIZIDE|GLIMEPIRIDE|PIOGLITAZONE"
)
if (!"suspect_drug_list" %in% names(ml)) ml[, suspect_drug_list := ""]
ml[is.na(suspect_drug_list), suspect_drug_list := ""]
for (nm in names(patterns)) {
  ml[, (nm) := as.integer(grepl(patterns[[nm]], suspect_drug_list, ignore.case = TRUE))]
}
drug_class_vars <- names(patterns)

cat("\nSplitting before imputation to keep train-only preprocessing.\n")
ml[, split := fifelse(report_year <= 2021, "train",
                      fifelse(report_year == 2022, "val", "test"))]
print(ml[, .N, by = split])

ml[, age_missing := as.integer(is.na(age_years))]
train_age_median <- median(ml[split == "train"]$age_years, na.rm = TRUE)
train_year_median <- median(ml[split == "train"]$report_year, na.rm = TRUE)
ml[is.na(age_years), age_years := train_age_median]
ml[is.na(tto_days), tto_days := 0]
ml[is.na(n_indications), n_indications := 0L]
ml[is.na(report_year), report_year := train_year_median]
ml[, sex_female := as.integer(sex == "F")]
ml[, sex_male := as.integer(sex == "M")]

bin_vars <- c("has_resp_failure", "has_pe", "has_pneumonia", "has_ild", "has_dyspnoea",
              "has_cardiac_ae", "has_renal_ae", "has_hepatic_ae",
              "has_cancer_indi", "has_diabetes_indi", "has_cvd_indi",
              "has_oral_route", "has_iv_route", "tto_available", drug_class_vars)
for (v in bin_vars) {
  if (v %in% names(ml)) ml[is.na(get(v)), (v) := 0L]
}

candidate_features <- unique(c(
  "age_years", "age_missing", "sex_female", "sex_male",
  "n_resp_pts", "has_resp_failure", "has_pe", "has_ild", "has_dyspnoea",
  "n_total_aes", "n_non_resp_aes", "has_cardiac_ae", "has_renal_ae", "has_hepatic_ae",
  "n_total_drugs", "n_suspect_drugs", "n_concomitant_drugs", "has_oral_route", "has_iv_route",
  drug_class_vars,
  "n_indications", "has_cancer_indi", "has_diabetes_indi", "has_cvd_indi",
  "tto_days", "tto_available",
  "report_year"
))
candidate_features <- candidate_features[candidate_features %in% names(ml)]
cat("Candidate features:", length(candidate_features), "\n")

cat("\nUnivariate screening on TRAIN ONLY...\n")
train_dt <- ml[split == "train"]
target <- train_dt$outc_death
uv_results <- list()
for (feat in candidate_features) {
  x <- train_dt[[feat]]
  vals <- unique(x[!is.na(x)])
  if (length(vals) <= 1) next
  if (length(vals) == 2) {
    tbl <- table(x, target)
    if (nrow(tbl) >= 2 && ncol(tbl) >= 2 && all(tbl > 0)) {
      test <- suppressWarnings(chisq.test(tbl, correct = FALSE))
      or_val <- (tbl[2, 2] * tbl[1, 1]) / (tbl[1, 2] * tbl[2, 1])
      uv_results[[feat]] <- data.table(Feature = feat, p_value = test$p.value,
                                       Effect = round(or_val, 4), test_type = "chi-square")
    }
  } else {
    x0 <- x[target == 0]
    x1 <- x[target == 1]
    if (length(x0) > 50000) x0 <- sample(x0, 50000)
    if (length(x1) > 50000) x1 <- sample(x1, 50000)
    test <- suppressWarnings(wilcox.test(x1, x0))
    uv_results[[feat]] <- data.table(Feature = feat, p_value = test$p.value,
                                     Effect = median(x1, na.rm = TRUE) - median(x0, na.rm = TRUE),
                                     test_type = "wilcoxon_median_diff")
  }
}
uv_dt <- rbindlist(uv_results, fill = TRUE)
uv_dt[, FDR := p.adjust(p_value, method = "BH")]
setorder(uv_dt, p_value)
fwrite(uv_dt, file.path(table_dir, "univariate_screening_2025Q4.csv"))
fwrite(uv_dt, file.path(results_dir, "univariate_screening_2025Q4.csv"))
print(uv_dt)

sig_features <- uv_dt[FDR < 0.05, Feature]
if (length(sig_features) < 5) {
  warning("Fewer than 5 BH-significant features; falling back to all candidate features.")
  sig_features <- candidate_features
}

cat("\nLASSO selection on TRAIN ONLY...\n")
X_lasso <- as.matrix(train_dt[, ..sig_features])
y_lasso <- train_dt$outc_death
X_lasso[is.na(X_lasso) | is.nan(X_lasso) | is.infinite(X_lasso)] <- 0
lasso_idx <- sample(nrow(X_lasso), min(200000, nrow(X_lasso)))
lasso_cv <- cv.glmnet(
  X_lasso[lasso_idx, , drop = FALSE], y_lasso[lasso_idx],
  family = "binomial", alpha = 1, nfolds = 5, type.measure = "auc"
)
coef_min <- coef(lasso_cv, s = "lambda.min")
coef_1se <- coef(lasso_cv, s = "lambda.1se")
final_features <- rownames(coef_min)[which(coef_min != 0)]
final_features <- setdiff(final_features, "(Intercept)")
lasso_selected_1se <- setdiff(rownames(coef_1se)[which(coef_1se != 0)], "(Intercept)")
if (length(final_features) == 0) final_features <- sig_features

cat("Selected lambda.min features:", length(final_features), "\n")
cat(paste(final_features, collapse = ", "), "\n")
cat("Selected lambda.1se features:", length(lasso_selected_1se), "\n")

label_map <- c(
  age_years = "Patient age (years)",
  age_missing = "Age data missing",
  sex_female = "Sex: female",
  sex_male = "Sex: male",
  n_resp_pts = "No. respiratory AE terms",
  has_resp_failure = "Respiratory failure/arrest",
  has_pe = "Pulmonary embolism",
  has_ild = "Interstitial lung disease/pneumonitis",
  has_dyspnoea = "Dyspnoea",
  n_total_aes = "Total no. adverse events",
  n_non_resp_aes = "No. non-respiratory AEs",
  has_cardiac_ae = "Cardiac co-reported AE",
  has_renal_ae = "Renal co-reported AE",
  has_hepatic_ae = "Hepatic co-reported AE",
  n_total_drugs = "Total no. drugs",
  n_suspect_drugs = "No. primary suspect drugs",
  n_concomitant_drugs = "No. concomitant drugs",
  has_oral_route = "Oral administration route",
  has_iv_route = "Intravenous administration route",
  drug_immune_checkpoint_inhibitor = "Immune checkpoint inhibitor",
  drug_tnf_inhibitor = "TNF-alpha inhibitor",
  drug_other_biologic = "Other biologic/JAK immunomodulator",
  drug_antineoplastic = "Antineoplastic/cytotoxic therapy",
  drug_targeted_therapy = "Targeted anticancer therapy",
  drug_anticoagulant = "Anticoagulant",
  drug_pah_therapy = "Pulmonary hypertension therapy",
  drug_antifibrotic = "Antifibrotic therapy",
  drug_inhaled_respiratory = "Inhaled respiratory therapy",
  drug_cardiovascular = "Cardiovascular medication",
  drug_antidiabetic = "Antidiabetic medication",
  n_indications = "No. indications",
  has_cancer_indi = "Cancer indication",
  has_diabetes_indi = "Diabetes indication",
  has_cvd_indi = "Cardiovascular indication",
  tto_days = "Time-to-onset (days)",
  tto_available = "Time-to-onset available",
  report_year = "Report year"
)

make_matrix <- function(dt, feats) {
  X <- as.matrix(dt[, ..feats])
  X[is.na(X) | is.nan(X) | is.infinite(X)] <- 0
  storage.mode(X) <- "double"
  X
}
X_train <- make_matrix(ml[split == "train"], final_features)
y_train <- ml[split == "train"]$outc_death
X_val <- make_matrix(ml[split == "val"], final_features)
y_val <- ml[split == "val"]$outc_death
X_test <- make_matrix(ml[split == "test"], final_features)
y_test <- ml[split == "test"]$outc_death

feature_manifest <- data.table(
  Feature = final_features,
  Label = ifelse(final_features %in% names(label_map), label_map[final_features], final_features),
  Selected_by = "train_only_lasso_lambda_min",
  In_lambda_1se = final_features %in% lasso_selected_1se,
  Univariate_FDR = uv_dt[match(final_features, Feature), FDR]
)
fwrite(feature_manifest, file.path(results_dir, "feature_manifest_2025Q4.csv"))
fwrite(feature_manifest, file.path(table_dir, "feature_manifest_2025Q4.csv"))
saveRDS(label_map, file.path(data_dir, "label_map_2025Q4.rds"))
fwrite(ml, file.path(data_dir, "ml_dataset_2025Q4.csv"))
save(ml, final_features, candidate_features, uv_dt, lasso_cv, lasso_selected_1se,
     feature_manifest, label_map, X_train, y_train, X_val, y_val, X_test, y_test,
     file = file.path(data_dir, "ml_ready_2025Q4.RData"))

split_summary <- ml[, .(
  N = .N,
  deaths = sum(outc_death == 1),
  death_rate = round(mean(outc_death == 1), 4),
  min_year = min(report_year),
  max_year = max(report_year)
), by = split][order(match(split, c("train", "val", "test")))]
fwrite(split_summary, file.path(results_dir, "split_summary_2025Q4.csv"))
cat("\nSplit summary:\n")
print(split_summary)
cat("\nSaved ml_ready_2025Q4.RData with", length(final_features), "features.\n")
cat("Completed:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
