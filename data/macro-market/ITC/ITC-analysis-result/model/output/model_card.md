# Model card

- Run: 20261010T153053-CHN-HS850811-RCEP-TOPSIS
- Scope: China / HS850811 / 14 foreign RCEP members, 11 complete markets.
- Main: five-indicator strategy TOPSIS; weights [0.3, 0.1, 0.1, 0.3, 0.2].
- Target: product-group market screening, not official ITC ranking or company-fit prediction.
- Reproducibility: input hashes, field lineage, normalization bounds, weighted matrices, ideal solutions, distances, entropy steps and sensitivity draws retained.
- Sources: existing official ITC data pack, original access timestamps preserved.
- Missing: Lao PDR, Myanmar, Viet Nam 2025 import-demand data; no imputation.
- Statistical limits: small cross-market sample, strategy weights, EPM and trade reference periods differ; Monte Carlo weight frequencies are not probabilities of success.
- See methodology.md and limitations.md for scope and provenance qualifications.
