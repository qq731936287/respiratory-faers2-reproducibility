#!/usr/bin/env Rscript

suppressPackageStartupMessages(library(data.table))

project_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
raw_dir <- file.path(project_root, "results", "easyfaers_resp_2025Q2_Q4_raw")
out_data_dir <- file.path(project_root, "data")
out_results_dir <- file.path(project_root, "results", "refresh_2025Q4")
log_dir <- file.path(project_root, "logs")
dir.create(out_data_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(out_results_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

log_file <- file.path(log_dir, "32_build_refreshed_dataset_2025Q4.log")
sink(log_file, split = TRUE)
on.exit(sink(), add = TRUE)

cat("============================================\n")
cat("32_build_refreshed_dataset_2025Q4\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("Raw dir:", raw_dir, "\n")
cat("============================================\n\n")

need <- c("demo.csv", "reac.csv", "outc.csv", "drug.csv", "indi.csv", "ther.csv")
missing_files <- need[!file.exists(file.path(raw_dir, need))]
if (length(missing_files)) {
  stop("Missing easyFAERS raw exports: ", paste(missing_files, collapse = ", "))
}

pt_lookup_path <- file.path(raw_dir, "respiratory_soc_pt_lookup_2025Q4.csv")
if (!file.exists(pt_lookup_path)) {
  stop("Missing respiratory SOC PT lookup: ", pt_lookup_path)
}
pt_lookup <- fread(pt_lookup_path)
resp_soc_pts <- sort(unique(pt_lookup$PT))

clean_names <- function(dt) {
  drop <- intersect(names(dt), c("V1", "Unnamed: 0"))
  if (length(drop)) dt[, (drop) := NULL]
  dt
}

parse_dt <- function(x) {
  x_num <- suppressWarnings(as.numeric(x))
  x_str <- as.character(as.integer(x_num))
  valid <- !is.na(x_num) & nchar(x_str) == 8
  out <- rep(NA_real_, length(x))
  if (any(valid)) {
    out[valid] <- as.numeric(as.Date(x_str[valid], format = "%Y%m%d"))
  }
  as.Date(out, origin = "1970-01-01")
}

cat("Loading easyFAERS 2025Q2-Q4 raw slices...\n")
demo <- clean_names(fread(file.path(raw_dir, "demo.csv")))
reac <- clean_names(fread(file.path(raw_dir, "reac.csv")))
outc <- clean_names(fread(file.path(raw_dir, "outc.csv")))
drug <- clean_names(fread(file.path(raw_dir, "drug.csv")))
indi <- clean_names(fread(file.path(raw_dir, "indi.csv")))
ther <- clean_names(fread(file.path(raw_dir, "ther.csv")))

for (dt in list(demo, reac, outc, drug, indi, ther)) {
  if (!"primaryid" %in% names(dt)) stop("A raw table is missing primaryid.")
}

cat(sprintf("Rows: demo=%s reac=%s outc=%s drug=%s indi=%s ther=%s\n",
            nrow(demo), nrow(reac), nrow(outc), nrow(drug), nrow(indi), nrow(ther)))
cat("Unique demo reports:", uniqueN(demo$primaryid), "\n")
cat("GetDataYear distribution:\n")
print(demo[, .N, by = GetDataYear][order(GetDataYear)])

if (!all(demo$GetDataYear %in% 252:254)) {
  warning("Demo contains GetDataYear outside 252:254; keeping rows but recording in summary.")
}

setnames(demo, "primaryid", "demo_pid")
demo[, age_years := fifelse(
  AGE_COD == "YR", as.numeric(AGE),
  fifelse(AGE_COD == "DEC", as.numeric(AGE) * 10,
  fifelse(AGE_COD == "MON", as.numeric(AGE) / 12,
  fifelse(AGE_COD == "WK", as.numeric(AGE) / 52,
  fifelse(AGE_COD == "DY", as.numeric(AGE) / 365,
  fifelse(AGE_COD == "HR", as.numeric(AGE) / 8760, NA_real_))))))
]
demo[age_years > 120 | age_years < 0, age_years := NA_real_]
demo[, report_year := 2000L + as.integer(floor(GetDataYear / 10))]
demo[, report_quarter := as.integer(GetDataYear %% 10)]
demo[, sex := fifelse(SEX %in% c("F", "M"), SEX, "Unknown")]
demo[, reporter_country := fifelse(!is.na(REPORTER_COUNTRY) & REPORTER_COUNTRY != "", REPORTER_COUNTRY, "Unknown")]
demo[, reporter_type := fifelse(
  OCCP_COD == "MD", "Physician",
  fifelse(OCCP_COD == "PH", "Pharmacist",
  fifelse(OCCP_COD == "CN", "Consumer",
  fifelse(OCCP_COD == "HP", "HealthProf",
  fifelse(OCCP_COD == "OT", "Other", "Unknown")))))
]

demo_features <- demo[, .(
  demo_pid, age_years, sex, reporter_country, reporter_type,
  report_year, report_quarter, FDA_DT, EVENT_DT
)]

cat("Building outcome features...\n")
outc_features <- outc[, .(
  outc_death = as.integer(any(OUTC_COD == "DE", na.rm = TRUE)),
  outc_hosp = as.integer(any(OUTC_COD == "HO", na.rm = TRUE)),
  outc_life_threat = as.integer(any(OUTC_COD == "LT", na.rm = TRUE)),
  outc_disability = as.integer(any(OUTC_COD == "DS", na.rm = TRUE)),
  outc_other = as.integer(any(OUTC_COD == "OT", na.rm = TRUE)),
  outc_serious = as.integer(any(OUTC_COD %in% c("DE", "HO", "LT", "DS", "CA", "RI"), na.rm = TRUE)),
  n_outc_types = uniqueN(OUTC_COD[!is.na(OUTC_COD) & OUTC_COD != "missing"])
), by = .(demo_pid = primaryid)]

cat("Building respiratory PT and co-AE features...\n")
reac[, demo_pid := primaryid]
resp_reac_detail <- reac[PT %in% resp_soc_pts, .(demo_pid, PT)]
resp_pt_features <- resp_reac_detail[, .(
  n_resp_pts = .N,
  resp_pt_list = paste(unique(PT), collapse = "|")
), by = demo_pid]

severe_pts <- c("RESPIRATORY FAILURE", "ACUTE RESPIRATORY FAILURE",
                "ACUTE RESPIRATORY DISTRESS SYNDROME", "RESPIRATORY ARREST",
                "CARDIO-RESPIRATORY ARREST")
pe_pts <- c("PULMONARY EMBOLISM", "PULMONARY THROMBOSIS")
pneumonia_pts <- c("PNEUMONIA", "PNEUMONIA ASPIRATION", "PNEUMONIA BACTERIAL",
                   "PNEUMONIA VIRAL", "COVID-19 PNEUMONIA",
                   "PNEUMOCYSTIS JIROVECII PNEUMONIA")
ild_pts <- c("INTERSTITIAL LUNG DISEASE", "PULMONARY FIBROSIS",
             "PNEUMONITIS", "ORGANISING PNEUMONIA")
dyspnoea_pts <- c("DYSPNOEA", "DYSPNOEA EXERTIONAL", "DYSPNOEA AT REST")

resp_flags <- resp_reac_detail[, .(
  has_resp_failure = as.integer(any(PT %in% severe_pts)),
  has_pe = as.integer(any(PT %in% pe_pts)),
  has_pneumonia = as.integer(any(PT %in% pneumonia_pts)),
  has_ild = as.integer(any(PT %in% ild_pts)),
  has_dyspnoea = as.integer(any(PT %in% dyspnoea_pts))
), by = demo_pid]

cardiac_pattern <- paste(c("CARDIAC", "MYOCARDIAL", "HEART", "ARRHYTHMIA", "TACHYCARDIA",
                           "BRADYCARDIA", "ATRIAL FIBRILLATION", "CARDIAC ARREST",
                           "CARDIAC FAILURE", "CARDIOMYOPATHY"), collapse = "|")
renal_pattern <- paste(c("RENAL", "KIDNEY", "NEPHRO", "ACUTE KIDNEY", "RENAL FAILURE"), collapse = "|")
hepatic_pattern <- paste(c("HEPAT", "LIVER", "JAUNDICE", "HEPATOTOXICITY",
                           "HEPATIC FAILURE", "HEPATITIS"), collapse = "|")

co_ae_features <- reac[, .(
  n_total_aes = uniqueN(PT),
  n_non_resp_aes = sum(!PT %in% resp_soc_pts, na.rm = TRUE),
  has_cardiac_ae = as.integer(any(grepl(cardiac_pattern, PT, ignore.case = TRUE))),
  has_renal_ae = as.integer(any(grepl(renal_pattern, PT, ignore.case = TRUE))),
  has_hepatic_ae = as.integer(any(grepl(hepatic_pattern, PT, ignore.case = TRUE)))
), by = demo_pid]

cat("Building drug features...\n")
drug[, demo_pid := primaryid]
drug_features <- drug[, .(
  n_total_drugs = uniqueN(DRUGNAME),
  n_suspect_drugs = sum(ROLE_COD == "PS", na.rm = TRUE),
  n_concomitant_drugs = sum(ROLE_COD == "C", na.rm = TRUE),
  n_secondary_suspect = sum(ROLE_COD == "SS", na.rm = TRUE),
  n_interacting = sum(ROLE_COD == "I", na.rm = TRUE),
  has_oral_route = as.integer(any(grepl("ORAL", ROUTE, ignore.case = TRUE))),
  has_iv_route = as.integer(any(grepl("INTRAVENOUS", ROUTE, ignore.case = TRUE))),
  suspect_drug_list = paste(unique(DRUGNAME[ROLE_COD == "PS"]), collapse = "|")
), by = demo_pid]

cat("Building indication features...\n")
indi[, demo_pid := primaryid]
cancer_pattern <- paste(c("NEOPLASM", "CANCER", "CARCINOMA", "LYMPHOMA", "LEUKEMIA",
                          "LEUKAEMIA", "MELANOMA", "SARCOMA", "MYELOMA", "TUMOR",
                          "TUMOUR", "MALIGNANT", "METASTA"), collapse = "|")
diabetes_pattern <- paste(c("DIABETES", "DIABETIC", "TYPE 2 DIABETES", "TYPE 1 DIABETES"), collapse = "|")
cvd_pattern <- paste(c("HYPERTENSION", "CORONARY", "HEART FAILURE", "ATRIAL FIBRILLATION",
                       "ISCHAEMIC HEART", "MYOCARDIAL INFARCTION"), collapse = "|")
indi_features <- indi[, .(
  n_indications = uniqueN(INDI_PT),
  has_cancer_indi = as.integer(any(grepl(cancer_pattern, INDI_PT, ignore.case = TRUE))),
  has_diabetes_indi = as.integer(any(grepl(diabetes_pattern, INDI_PT, ignore.case = TRUE))),
  has_cvd_indi = as.integer(any(grepl(cvd_pattern, INDI_PT, ignore.case = TRUE))),
  primary_indi = INDI_PT[1]
), by = demo_pid]

cat("Building therapy features...\n")
ther[, demo_pid := primaryid]
ther_features <- ther[, .(
  has_start_dt = as.integer(any(!is.na(START_DT))),
  has_end_dt = as.integer(any(!is.na(END_DT))),
  min_start_dt = suppressWarnings(min(as.double(START_DT), na.rm = TRUE)),
  max_end_dt = suppressWarnings(max(as.double(END_DT), na.rm = TRUE))
), by = demo_pid]
ther_features[is.infinite(min_start_dt), min_start_dt := NA_real_]
ther_features[is.infinite(max_end_dt), max_end_dt := NA_real_]

cat("Merging refreshed quarter features...\n")
new_data <- copy(demo_features)
for (obj in list(outc_features, resp_pt_features, resp_flags, co_ae_features,
                 drug_features, indi_features, ther_features)) {
  new_data <- merge(new_data, obj, by = "demo_pid", all.x = TRUE)
}

outc_cols <- c("outc_death", "outc_hosp", "outc_life_threat", "outc_disability",
               "outc_other", "outc_serious", "n_outc_types")
new_data[, outc_missing := as.integer(is.na(n_outc_types) | n_outc_types == 0)]
for (v in setdiff(outc_cols, "n_outc_types")) new_data[is.na(get(v)), (v) := 0L]
new_data[is.na(n_outc_types), n_outc_types := 0L]

new_data[, event_date := parse_dt(EVENT_DT)]
new_data[, start_date := parse_dt(min_start_dt)]
new_data[, tto_days := as.numeric(difftime(event_date, start_date, units = "days"))]
new_data[tto_days < 0 | tto_days > 7300, tto_days := NA_real_]
new_data[, tto_available := as.integer(!is.na(tto_days))]

cat("Loading existing Q1-2025 dataset and appending Q2-Q4...\n")
load(file.path(out_data_dir, "respiratory_ae_data.RData"))
old_full <- copy(final_data)
rm(final_data)
if (exists("ml_data")) rm(ml_data)

overlap <- intersect(old_full$demo_pid, new_data$demo_pid)
cat("Overlap with existing data:", length(overlap), "\n")
if (length(overlap)) {
  cat("Dropping overlapping old rows before append.\n")
  old_full <- old_full[!demo_pid %in% overlap]
}

common_cols <- union(names(old_full), names(new_data))
for (v in setdiff(common_cols, names(old_full))) old_full[, (v) := NA]
for (v in setdiff(common_cols, names(new_data))) new_data[, (v) := NA]
setcolorder(old_full, common_cols)
setcolorder(new_data, common_cols)

final_data_2025Q4 <- rbindlist(list(old_full, new_data), use.names = TRUE, fill = TRUE)
setorder(final_data_2025Q4, report_year, report_quarter, demo_pid)
ml_data_2025Q4 <- final_data_2025Q4[outc_missing == 0]

summary_year <- final_data_2025Q4[, .(
  N = .N,
  known_outcome = sum(outc_missing == 0, na.rm = TRUE),
  deaths = sum(outc_death == 1, na.rm = TRUE),
  death_rate_known = round(mean(outc_death[outc_missing == 0] == 1, na.rm = TRUE), 4)
), by = .(report_year, report_quarter)][order(report_year, report_quarter)]

summary_overall <- data.table(
  dataset = c("final_data_2025Q4", "ml_data_2025Q4", "new_2025Q2_Q4"),
  rows = c(nrow(final_data_2025Q4), nrow(ml_data_2025Q4), nrow(new_data)),
  deaths = c(sum(final_data_2025Q4$outc_death == 1, na.rm = TRUE),
             sum(ml_data_2025Q4$outc_death == 1, na.rm = TRUE),
             sum(new_data$outc_death == 1, na.rm = TRUE)),
  min_year = c(min(final_data_2025Q4$report_year, na.rm = TRUE),
               min(ml_data_2025Q4$report_year, na.rm = TRUE),
               min(new_data$report_year, na.rm = TRUE)),
  max_year = c(max(final_data_2025Q4$report_year, na.rm = TRUE),
               max(ml_data_2025Q4$report_year, na.rm = TRUE),
               max(new_data$report_year, na.rm = TRUE))
)

fwrite(new_data, file.path(out_results_dir, "respiratory_ae_2025Q2_Q4_feature_rows.csv"))
fwrite(summary_year, file.path(out_results_dir, "year_quarter_summary_2025Q4.csv"))
fwrite(summary_overall, file.path(out_results_dir, "data_refresh_summary.csv"))
fwrite(final_data_2025Q4, file.path(out_data_dir, "respiratory_ae_full_2025Q4.csv"))
fwrite(ml_data_2025Q4, file.path(out_data_dir, "respiratory_ae_ml_2025Q4.csv"))
save(final_data_2025Q4, ml_data_2025Q4,
     file = file.path(out_data_dir, "respiratory_ae_data_2025Q4.RData"))

cat("\nOverall summary:\n")
print(summary_overall)
cat("\nLast quarters:\n")
print(tail(summary_year, 12))
cat("\nSaved refreshed data objects under data/*_2025Q4.*\n")
cat("Completed:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
