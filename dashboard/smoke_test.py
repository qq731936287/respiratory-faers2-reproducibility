from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
required = [
    ROOT / "output/bigdata_si/agentic_layer/agent_decisions.csv",
    ROOT / "output/bigdata_si/agentic_layer/openfda_federated_audit.csv",
    ROOT / "results/model_2025Q4/model_comparison_2025Q4.csv",
    ROOT / "results/model_2025Q4/shap_importance_2025Q4.csv",
    ROOT / "results/model_2025Q4/subgroup_performance_2025Q4.csv",
]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise SystemExit("Missing dashboard inputs: " + "; ".join(missing))
print("Dashboard smoke test passed.")
