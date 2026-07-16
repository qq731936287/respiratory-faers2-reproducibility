#!/usr/bin/env Rscript

suppressPackageStartupMessages({
  library(data.table)
  library(glmnet)
  library(xgboost)
  library(lightgbm)
  library(ranger)
  library(pROC)
  library(PRROC)
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

log_file <- file.path(log_dir, "34_train_models_2025Q4.log")
sink(log_file, split = TRUE)
on.exit(sink(), add = TRUE)

cat("============================================\n")
cat("34_train_models_2025Q4\n")
cat("Started:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
cat("============================================\n\n")

load(file.path(data_dir, "ml_ready_2025Q4.RData"))
cat("Feature count:", length(final_features), "\n")
cat("Train:", nrow(X_train), "Val:", nrow(X_val), "Test:", nrow(X_test), "\n")
cat("Train death rate:", round(mean(y_train == 1), 4), "\n")
cat("Val death rate:", round(mean(y_val == 1), 4), "\n")
cat("Test death rate:", round(mean(y_test == 1), 4), "\n\n")

safe_div <- function(a, b) ifelse(b == 0, NA_real_, a / b)

threshold_from_val <- function(y_true, y_prob) {
  roc_obj <- pROC::roc(y_true, y_prob, quiet = TRUE)
  as.numeric(pROC::coords(roc_obj, "best", best.method = "youden", ret = "threshold"))
}

metric_one <- function(y_true, y_prob, threshold) {
  roc_obj <- pROC::roc(y_true, y_prob, quiet = TRUE)
  auroc <- as.numeric(pROC::auc(roc_obj))
  pr_obj <- PRROC::pr.curve(scores.class0 = y_prob[y_true == 1],
                            scores.class1 = y_prob[y_true == 0])
  auprc <- pr_obj$auc.integral
  y_pred <- as.integer(y_prob >= threshold)
  tp <- sum(y_pred == 1 & y_true == 1)
  fp <- sum(y_pred == 1 & y_true == 0)
  fn <- sum(y_pred == 0 & y_true == 1)
  tn <- sum(y_pred == 0 & y_true == 0)
  data.table(
    AUROC = auroc,
    AUPRC = auprc,
    Sensitivity = safe_div(tp, tp + fn),
    Specificity = safe_div(tn, tn + fp),
    PPV = safe_div(tp, tp + fp),
    NPV = safe_div(tn, tn + fn),
    F1 = safe_div(2 * tp, 2 * tp + fp + fn),
    Threshold = threshold,
    Brier = mean((y_prob - y_true)^2)
  )
}

calibrate_from_val <- function(val_prob, val_y, test_prob) {
  eps <- 1e-6
  val_logit <- qlogis(pmin(pmax(val_prob, eps), 1 - eps))
  test_logit <- qlogis(pmin(pmax(test_prob, eps), 1 - eps))
  fit <- glm(val_y ~ val_logit, family = binomial())
  as.numeric(predict(fit, newdata = data.frame(val_logit = test_logit), type = "response"))
}

calibration_stats <- function(y, p) {
  eps <- 1e-6
  p2 <- pmin(pmax(p, eps), 1 - eps)
  fit <- glm(y ~ qlogis(p2), family = binomial())
  data.table(
    Brier = mean((p - y)^2),
    Calibration_Intercept = unname(coef(fit)[1]),
    Calibration_Slope = unname(coef(fit)[2]),
    Expected_Observed = sum(p) / sum(y)
  )
}

bootstrap_auprc <- function(y, p, reps = 200L) {
  set.seed(42)
  n <- length(y)
  vals <- numeric(reps)
  for (i in seq_len(reps)) {
    idx <- sample.int(n, n, replace = TRUE)
    vals[i] <- PRROC::pr.curve(scores.class0 = p[idx][y[idx] == 1],
                               scores.class1 = p[idx][y[idx] == 0])$auc.integral
  }
  quantile(vals, c(0.025, 0.975), na.rm = TRUE)
}

model_preds <- list()
val_preds <- list()
thresholds <- list()
models <- list()

scale_pos <- sum(y_train == 0) / sum(y_train == 1)

cat("--- Logistic regression (elastic-net) ---\n")
t0 <- Sys.time()
lr_model <- cv.glmnet(X_train, y_train, family = "binomial", alpha = 0.5,
                      nfolds = 5, type.measure = "auc")
val_preds[["Logistic Regression"]] <- as.numeric(predict(lr_model, X_val, s = "lambda.min", type = "response"))
model_preds[["Logistic Regression"]] <- as.numeric(predict(lr_model, X_test, s = "lambda.min", type = "response"))
thresholds[["Logistic Regression"]] <- threshold_from_val(y_val, val_preds[["Logistic Regression"]])
models[["Logistic Regression"]] <- lr_model
saveRDS(lr_model, file.path(data_dir, "model_lr_2025Q4.rds"))
cat("Done in", round(difftime(Sys.time(), t0, units = "mins"), 2), "min\n\n")

cat("--- XGBoost ---\n")
t0 <- Sys.time()
dtrain <- xgb.DMatrix(X_train, label = y_train)
dval <- xgb.DMatrix(X_val, label = y_val)
dtest <- xgb.DMatrix(X_test, label = y_test)
xgb_params <- list(
  objective = "binary:logistic", eval_metric = "auc",
  max_depth = 5, eta = 0.08, min_child_weight = 8,
  subsample = 0.8, colsample_bytree = 0.8,
  scale_pos_weight = scale_pos, gamma = 1, lambda = 1, alpha = 0.1,
  nthread = max(1L, parallel::detectCores() - 2L)
)
xgb_model <- xgb.train(
  params = xgb_params, data = dtrain, nrounds = 600,
  watchlist = list(train = dtrain, val = dval),
  early_stopping_rounds = 40, print_every_n = 100, verbose = 1
)
val_preds[["XGBoost"]] <- predict(xgb_model, dval)
model_preds[["XGBoost"]] <- predict(xgb_model, dtest)
thresholds[["XGBoost"]] <- threshold_from_val(y_val, val_preds[["XGBoost"]])
models[["XGBoost"]] <- xgb_model
xgb.save(xgb_model, file.path(data_dir, "model_xgb_2025Q4.json"))
xgb_importance <- xgb.importance(model = xgb_model)
xgb_importance[, Label := ifelse(Feature %in% names(label_map), label_map[Feature], Feature)]
fwrite(xgb_importance, file.path(data_dir, "xgb_importance_2025Q4.csv"))
cat("Done in", round(difftime(Sys.time(), t0, units = "mins"), 2), "min\n\n")

cat("--- LightGBM ---\n")
t0 <- Sys.time()
dtrain_lgb <- lgb.Dataset(X_train, label = y_train)
dval_lgb <- lgb.Dataset(X_val, label = y_val, reference = dtrain_lgb)
lgb_model <- lgb.train(
  params = list(objective = "binary", metric = "auc", learning_rate = 0.08,
                max_depth = 5, num_leaves = 31, min_data_in_leaf = 40,
                bagging_fraction = 0.8, bagging_freq = 1,
                feature_fraction = 0.8, scale_pos_weight = scale_pos,
                num_threads = max(1L, parallel::detectCores() - 2L), verbose = -1),
  data = dtrain_lgb, nrounds = 600, valids = list(val = dval_lgb),
  early_stopping_rounds = 40
)
val_preds[["LightGBM"]] <- predict(lgb_model, X_val)
model_preds[["LightGBM"]] <- predict(lgb_model, X_test)
thresholds[["LightGBM"]] <- threshold_from_val(y_val, val_preds[["LightGBM"]])
models[["LightGBM"]] <- lgb_model
lgb.save(lgb_model, file.path(data_dir, "model_lgb_2025Q4.txt"))
cat("Done in", round(difftime(Sys.time(), t0, units = "mins"), 2), "min\n\n")

cat("--- Random forest (ranger, train subsample) ---\n")
t0 <- Sys.time()
rf_n <- min(150000L, nrow(X_train))
rf_idx <- sample.int(nrow(X_train), rf_n)
rf_dt <- as.data.frame(X_train[rf_idx, , drop = FALSE])
rf_dt$outcome <- factor(y_train[rf_idx], levels = c(0, 1))
rf_model <- ranger(
  outcome ~ ., data = rf_dt, probability = TRUE,
  num.trees = 400, mtry = max(1L, floor(sqrt(ncol(X_train)))),
  importance = "impurity", seed = 42,
  case.weights = ifelse(y_train[rf_idx] == 1, scale_pos, 1),
  num.threads = max(1L, parallel::detectCores() - 2L)
)
val_preds[["Random Forest"]] <- predict(rf_model, data = as.data.frame(X_val))$predictions[, "1"]
model_preds[["Random Forest"]] <- predict(rf_model, data = as.data.frame(X_test))$predictions[, "1"]
thresholds[["Random Forest"]] <- threshold_from_val(y_val, val_preds[["Random Forest"]])
models[["Random Forest"]] <- rf_model
saveRDS(rf_model, file.path(data_dir, "model_rf_2025Q4.rds"))
rf_importance <- data.table(Feature = names(rf_model$variable.importance),
                            Importance = as.numeric(rf_model$variable.importance))
rf_importance[, Label := ifelse(Feature %in% names(label_map), label_map[Feature], Feature)]
setorder(rf_importance, -Importance)
fwrite(rf_importance, file.path(data_dir, "rf_importance_2025Q4.csv"))
cat("Done in", round(difftime(Sys.time(), t0, units = "mins"), 2), "min\n\n")

cat("Evaluating models...\n")
metrics <- rbindlist(lapply(names(model_preds), function(m) {
  base <- metric_one(y_test, model_preds[[m]], thresholds[[m]])
  base[, `:=`(Model = m, Dataset = "test_uncalibrated")]
  setcolorder(base, c("Model", "Dataset"))
  base
}))

calibrated_preds <- lapply(names(model_preds), function(m) {
  calibrate_from_val(val_preds[[m]], y_val, model_preds[[m]])
})
names(calibrated_preds) <- names(model_preds)

calibrated_val_preds <- lapply(names(val_preds), function(m) {
  calibrate_from_val(val_preds[[m]], y_val, val_preds[[m]])
})
names(calibrated_val_preds) <- names(val_preds)

calibrated_thresholds <- lapply(names(calibrated_val_preds), function(m) {
  threshold_from_val(y_val, calibrated_val_preds[[m]])
})
names(calibrated_thresholds) <- names(calibrated_val_preds)

cal_metrics <- rbindlist(lapply(names(calibrated_preds), function(m) {
  base <- metric_one(y_test, calibrated_preds[[m]], calibrated_thresholds[[m]])
  cstats <- calibration_stats(y_test, calibrated_preds[[m]])
  base[, `:=`(
    Brier = cstats$Brier,
    Calibration_Intercept = cstats$Calibration_Intercept,
    Calibration_Slope = cstats$Calibration_Slope,
    Expected_Observed = cstats$Expected_Observed,
    Model = m,
    Dataset = "test_validation_calibrated"
  )]
  setcolorder(base, c("Model", "Dataset"))
  base
}))
metrics[, `:=`(Calibration_Intercept = NA_real_, Calibration_Slope = NA_real_, Expected_Observed = NA_real_)]
all_metrics <- rbindlist(list(metrics, cal_metrics), fill = TRUE)

cat("Computing AUROC DeLong CI and AUPRC bootstrap CI (200 reps)...\n")
ci_rows <- rbindlist(lapply(names(model_preds), function(m) {
  p <- calibrated_preds[[m]]
  roc_obj <- pROC::roc(y_test, p, quiet = TRUE)
  auc_ci <- as.numeric(pROC::ci.auc(roc_obj, method = "delong"))
  pr_ci <- as.numeric(bootstrap_auprc(y_test, p, reps = 200L))
  data.table(
    Model = m,
    AUROC_low = auc_ci[1],
    AUROC_mid = auc_ci[2],
    AUROC_high = auc_ci[3],
    AUPRC_low = pr_ci[1],
    AUPRC_high = pr_ci[2],
    CI_method = "AUROC DeLong; AUPRC nonparametric bootstrap, 200 replicates"
  )
}))

test_predictions <- data.table(y_true = y_test)
val_predictions <- data.table(y_true = y_val)
for (m in names(model_preds)) {
  key <- make.names(tolower(m))
  test_predictions[, paste0(key, "_prob") := model_preds[[m]]]
  test_predictions[, paste0(key, "_prob_calibrated") := calibrated_preds[[m]]]
  val_predictions[, paste0(key, "_prob") := val_preds[[m]]]
  val_predictions[, paste0(key, "_prob_calibrated") := calibrated_val_preds[[m]]]
}

roc_plot_data <- rbindlist(lapply(names(calibrated_preds), function(m) {
  roc_obj <- pROC::roc(y_test, calibrated_preds[[m]], quiet = TRUE)
  data.table(Model = m, FPR = 1 - roc_obj$specificities, TPR = roc_obj$sensitivities)
}))

pr_plot_data <- rbindlist(lapply(names(calibrated_preds), function(m) {
  ord <- order(calibrated_preds[[m]], decreasing = TRUE)
  y <- y_test[ord]
  tp <- cumsum(y == 1)
  fp <- cumsum(y == 0)
  data.table(Model = m, Recall = tp / sum(y == 1), Precision = tp / pmax(tp + fp, 1))
}))

fwrite(all_metrics, file.path(table_dir, "model_comparison_2025Q4.csv"))
fwrite(all_metrics, file.path(results_dir, "model_comparison_2025Q4.csv"))
fwrite(ci_rows, file.path(results_dir, "model_metric_ci_2025Q4.csv"))
fwrite(test_predictions, file.path(data_dir, "test_predictions_2025Q4.csv"))
fwrite(val_predictions, file.path(data_dir, "val_predictions_2025Q4.csv"))
fwrite(roc_plot_data, file.path(data_dir, "roc_plot_data_2025Q4.csv"))
fwrite(pr_plot_data, file.path(data_dir, "pr_plot_data_2025Q4.csv"))

save(models, model_preds, val_preds, calibrated_preds, calibrated_val_preds,
     thresholds, calibrated_thresholds,
     all_metrics, ci_rows, roc_plot_data, pr_plot_data,
     file = file.path(data_dir, "ml_results_2025Q4.RData"))

writeLines(capture.output(sessionInfo()), file.path(results_dir, "sessionInfo_34_train_models_2025Q4.txt"))

cat("\nModel comparison:\n")
print(all_metrics)
cat("\nMetric CIs:\n")
print(ci_rows)
cat("\nSaved model artifacts and predictions.\n")
cat("Completed:", format(Sys.time(), "%Y-%m-%d %H:%M:%S %Z"), "\n")
