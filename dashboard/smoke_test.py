from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = [
    ROOT / "release_results/agent_decisions.csv",
    ROOT / "release_results/openfda_federated_audit.csv",
    ROOT / "release_results/model_comparison_2025Q4.csv",
    ROOT / "release_results/shap_importance_2025Q4.csv",
    ROOT / "release_results/subgroup_performance_2025Q4.csv",
]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise SystemExit("Missing dashboard inputs: " + "; ".join(missing))
print("Dashboard smoke test passed.")
