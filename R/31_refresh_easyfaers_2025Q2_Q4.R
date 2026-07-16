#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(easyFAERS)
})

project_root <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
faers_dict_dir <- Sys.getenv("FAERS_INPUT_DIR", unset = "")
if (!nzchar(faers_dict_dir)) {
  stop("Set FAERS_INPUT_DIR to a local directory containing the FDA/easyFAERS input files.")
}
faers_dict_dir <- normalizePath(faers_dict_dir, winslash = "/", mustWork = TRUE)
pt_lookup_path <- file.path(faers_dict_dir, "PT查询(2004Q1-2025Q4).csv")
out_dir <- file.path(project_root, "results", "easyfaers_resp_2025Q2_Q4_raw")
log_dir <- file.path(project_root, "logs")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(log_dir, recursive = TRUE, showWarnings = FALSE)

log_file <- file.path(log_dir, "31_refresh_easyfaers_2025Q2_Q4.log")
sink(log_file, split = TRUE)
on.exit(sink(), add = TRUE)

cat("============================================\n")
cat("31_refresh_easyfaers_2025Q2_Q4\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("Project root:", project_root, "\n")
cat("FAERS dictionary dir:", faers_dict_dir, "\n")
cat("Output dir:", out_dir, "\n")
cat("============================================\n\n")

if (!file.exists(pt_lookup_path)) {
  stop("PT lookup not found: ", pt_lookup_path)
}

pt_lookup <- fread(pt_lookup_path)
required_cols <- c("PT", "soc_name_en")
if (!all(required_cols %in% names(pt_lookup))) {
  stop("PT lookup missing required columns: ", paste(setdiff(required_cols, names(pt_lookup)), collapse = ", "))
}

resp_pts <- sort(unique(pt_lookup[
  soc_name_en == "RESPIRATORY, THORACIC AND MEDIASTINAL DISORDERS" & !is.na(PT),
  PT
]))
cat("Respiratory SOC PTs:", length(resp_pts), "\n")
cat("First PTs:", paste(head(resp_pts, 10), collapse = " | "), "\n\n")

writeLines(resp_pts, file.path(out_dir, "respiratory_soc_pt_list_2025Q4.txt"))
fwrite(pt_lookup[soc_name_en == "RESPIRATORY, THORACIC AND MEDIASTINAL DISORDERS"],
       file.path(out_dir, "respiratory_soc_pt_lookup_2025Q4.csv"))

cat("Configuring easyFAERS local dictionary path...\n")
locate_FAERS(path = faers_dict_dir)

cat("\nRunning BFun for 2025Q2-Q4 (GetDataYear 252-254)...\n")
cat("This should export raw 7-table slices plus easyFAERS summaries.\n")
flush.console()

res <- BFun(
  ptname = resp_pts,
  year = c(252, 254),
  path = out_dir
)

cat("\nBFun returned:\n")
print(res)

cat("\nExported files:\n")
exported <- list.files(out_dir, recursive = TRUE, full.names = TRUE)
print(data.table(
  file = basename(exported),
  size_mb = round(file.info(exported)$size / 1024^2, 3),
  modified = format(file.info(exported)$mtime, "%Y-%m-%d %H:%M:%S")
)[order(file)])

cat("\nCompleted:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
