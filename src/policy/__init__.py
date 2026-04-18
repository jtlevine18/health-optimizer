"""Decision-Focused Learning policy module.

Phase 2 of the LastMileBench Kenya migration. Provides:
  - features.build_dp_features: DP -> feature dict
  - train_dfl: CLI training script that produces models/dfl_v1.lgbm.txt
  - dfl_policy: pure-inference wrapper used by both the production
    pipeline (Phase 2.4) and the benchmark adapter (Phase 3).
"""
