from pathlib import Path
import csv
import math
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "sources" / "20260905-CHN-Roborock-HS85098090-rcep-v01" / "model_inputs.csv"
OUT = ROOT / "main" / "graphics"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.sans-serif": ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"],
    "axes.unicode_minus": False,
    "figure.dpi": 160,
    "savefig.dpi": 220,
    "axes.edgecolor": "#68717a",
    "axes.labelcolor": "#27313a",
    "xtick.color": "#4c5660",
    "ytick.color": "#4c5660",
    "text.color": "#27313a",
})

df = pd.read_csv(INPUT)
complete = df.dropna(subset=[
    "imports_2025_usd_thousand", "import_cagr_2020_2025_pct",
    "china_share_2025_pct", "epi_potential_usd", "untapped_potential_usd"
]).copy()
names = {
    "Australia": "澳大利亚", "Brunei Darussalam": "文莱", "Cambodia": "柬埔寨",
    "Indonesia": "印度尼西亚", "Japan": "日本", "Korea, Republic of": "韩国",
    "Malaysia": "马来西亚", "New Zealand": "新西兰", "Philippines": "菲律宾",
    "Singapore": "新加坡", "Thailand": "泰国", "Germany": "德国",
    "Viet Nam": "越南", "Myanmar": "缅甸",
    "Lao People's Democratic Republic": "老挝",
}
complete["market"] = complete["country_name"].map(names)

# 1. Market size and growth: 11 complete markets, same analytical grain.
fig, ax = plt.subplots(figsize=(8.6, 5.2))
colors = ["#d28b26" if n in {"日本", "韩国", "澳大利亚"} else "#4f79a7" for n in complete["market"]]
sizes = 35 + complete["china_share_2025_pct"] * 2.2
ax.scatter(complete["imports_2025_usd_thousand"] / 1000,
           complete["import_cagr_2020_2025_pct"], s=sizes, c=colors,
           alpha=0.85, edgecolor="white", linewidth=0.8)
for _, r in complete.iterrows():
    ax.annotate(r["market"], (r["imports_2025_usd_thousand"] / 1000,
                r["import_cagr_2020_2025_pct"]), xytext=(5, 4),
                textcoords="offset points", fontsize=8)
ax.axhline(0, color="#68717a", lw=0.8)
ax.set_xscale("log")
ax.set_xlabel("2025年进口额（百万美元，对数刻度）")
ax.set_ylabel("2020—2025年进口CAGR（%）")
ax.set_title("RCEP候选市场的规模、增长与中国供应份额")
ax.text(0, -0.20, "气泡面积表示2025年中国供应份额；橙色为筛选出的前三市场。",
        transform=ax.transAxes, fontsize=8.5, color="#4c5660")
ax.grid(axis="both", color="#d9dde2", lw=0.6, alpha=0.7)
fig.tight_layout()
fig.savefig(OUT / "market_size_growth.pdf", bbox_inches="tight")
fig.savefig(OUT / "market_size_growth.png", bbox_inches="tight", dpi=220)
plt.close(fig)

# 2. EPI potential and untapped potential for all 14 markets.
epi = df.sort_values("epi_potential_usd", ascending=True).copy()
epi["market"] = epi["country_name"].map(names).fillna(epi["country_name"])
fig, ax = plt.subplots(figsize=(8.6, 6.2))
y = np.arange(len(epi))
ax.barh(y, epi["epi_potential_usd"] / 1e6, color="#dce7f2", edgecolor="#4f79a7", label="EPI潜力")
ax.barh(y, epi["untapped_potential_usd"] / 1e6, color="#d28b26", label="未实现潜力")
ax.set_yticks(y, epi["market"])
ax.set_xlabel("百万美元")
ax.set_title("ITC出口潜力与未实现潜力")
ax.legend(frameon=False, loc="lower right")
ax.grid(axis="x", color="#d9dde2", lw=0.6, alpha=0.7)
fig.tight_layout()
fig.savefig(OUT / "epi_untapped.pdf", bbox_inches="tight")
fig.savefig(OUT / "epi_untapped.png", bbox_inches="tight", dpi=220)
plt.close(fig)

# 3. Supplier concentration in the three selected markets.
supplier_files = {
    "日本": ROOT / "output-restrictions" / "raw-material" / "ITC-data" / "japan" / "derived" / "top_suppliers_2025.csv",
    "韩国": ROOT / "output-restrictions" / "raw-material" / "ITC-data" / "south-korea" / "derived" / "top_suppliers_2025.csv",
    "澳大利亚": ROOT / "output-restrictions" / "raw-material" / "ITC-data" / "australia" / "derived" / "top_suppliers_2025.csv",
}
supplier_rows = []
for market, path in supplier_files.items():
    suppliers = pd.read_csv(path).sort_values("rank_2025")
    china = suppliers.loc[suppliers["supplier_name"] == "China"].iloc[0]
    second = suppliers.loc[suppliers["rank_2025"] == 2].iloc[0]
    supplier_rows.append({
        "market": market,
        "china_share": china["share_2025_pct"],
        "second_name": names.get(second["supplier_name"], second["supplier_name"]),
        "second_share": second["share_2025_pct"],
        "other_share": 100 - china["share_2025_pct"] - second["share_2025_pct"],
    })
supplier_df = pd.DataFrame(supplier_rows)
fig, ax = plt.subplots(figsize=(8.6, 4.8))
x = np.arange(len(supplier_df))
ax.bar(x, supplier_df["china_share"], color="#d28b26", label="中国")
ax.bar(x, supplier_df["second_share"], bottom=supplier_df["china_share"],
       color="#4f79a7", label="第二供应国")
ax.bar(x, supplier_df["other_share"],
       bottom=supplier_df["china_share"] + supplier_df["second_share"],
       color="#d9dde2", label="其他供应国")
for i, row in supplier_df.iterrows():
    ax.text(i, row["china_share"] / 2, f'{row["china_share"]:.1f}%',
            ha="center", va="center", color="white", fontsize=9, fontweight="bold")
    ax.text(i, row["china_share"] + row["second_share"] / 2,
            f'{row["second_name"]}\n{row["second_share"]:.1f}%',
            ha="center", va="center", color="white", fontsize=8)
ax.set_xticks(x, supplier_df["market"])
ax.set_ylim(0, 100)
ax.set_ylabel("2025年进口份额（%）")
ax.set_title("前三市场的供应来源集中度")
ax.legend(frameon=False, loc="upper center", ncol=3, bbox_to_anchor=(0.5, -0.12))
ax.grid(axis="y", color="#d9dde2", lw=0.6, alpha=0.7)
fig.tight_layout()
fig.savefig(OUT / "supplier_concentration.pdf", bbox_inches="tight")
fig.savefig(OUT / "supplier_concentration.png", bbox_inches="tight", dpi=220)
plt.close(fig)

# 4. Transparent normalized score. Amount indicators use log1p.
complete["untapped_ratio"] = complete["untapped_potential_usd"] / complete["epi_potential_usd"]
indicators = {
    "market_size": np.log1p(complete["imports_2025_usd_thousand"]),
    "market_growth": complete["import_cagr_2020_2025_pct"],
    "china_position": complete["china_share_2025_pct"],
    "untapped_amount": np.log1p(complete["untapped_potential_usd"]),
    "untapped_ratio": complete["untapped_ratio"],
}
z = pd.DataFrame(index=complete.index)
for k, s in indicators.items():
    lo, hi = s.min(), s.max()
    z[k] = (s - lo) / (hi - lo) if hi > lo else 0.0
weights = np.array([0.30, 0.10, 0.10, 0.30, 0.20])
zmat = z[list(indicators)].to_numpy()
weighted = zmat * weights
ideal_best = weighted.max(axis=0)
ideal_worst = weighted.min(axis=0)
d_plus = np.sqrt(((weighted - ideal_best) ** 2).sum(axis=1))
d_minus = np.sqrt(((weighted - ideal_worst) ** 2).sum(axis=1))
complete["score"] = d_minus / (d_plus + d_minus)
ranked = complete.sort_values("score", ascending=True)
fig, ax = plt.subplots(figsize=(8.6, 5.4))
bar_colors = ["#d28b26" if m in {"日本", "韩国", "澳大利亚"} else "#4f79a7" for m in ranked["market"]]
ax.barh(ranked["market"], ranked["score"], color=bar_colors, edgecolor="white")
for i, v in enumerate(ranked["score"]):
    ax.text(v + 0.008, i, f"{v:.3f}", va="center", fontsize=8)
ax.set_xlim(0, min(1.0, ranked["score"].max() + 0.12))
ax.set_xlabel("归一化综合得分（0—1）")
ax.set_title("五指标战略权重TOPSIS市场吸引力得分")
ax.grid(axis="x", color="#d9dde2", lw=0.6, alpha=0.7)
fig.tight_layout()
fig.savefig(OUT / "market_score.pdf", bbox_inches="tight")
fig.savefig(OUT / "market_score.png", bbox_inches="tight", dpi=220)
plt.close(fig)

# 5. Sensitivity: random weights around the five indicators, deterministic seed.
rng = np.random.default_rng(850980)
draws = rng.dirichlet(weights * 40, size=5000)
scores = np.zeros((len(complete), len(draws)))
for j, w in enumerate(draws):
    vw = zmat * w
    best = vw.max(axis=0)
    worst = vw.min(axis=0)
    dp = np.sqrt(((vw - best) ** 2).sum(axis=1))
    dm = np.sqrt(((vw - worst) ** 2).sum(axis=1))
    scores[:, j] = dm / (dp + dm)
ranks = np.argsort(np.argsort(-scores, axis=0), axis=0) + 1
sens = []
for pos, idx in enumerate(complete.index):
    rr = ranks[pos]
    sens.append({
        "country_name": complete.loc[idx, "country_name"],
        "market": complete.loc[idx, "market"],
        "base_score": complete.loc[idx, "score"],
        "mean_rank": rr.mean(),
        "best_rank": rr.min(),
        "worst_rank": rr.max(),
        "top3_share": (rr <= 3).mean(),
    })
sens_df = pd.DataFrame(sens).sort_values("mean_rank")
sens_df.to_csv(ROOT / "sources" / "20260905-CHN-Roborock-HS85098090-rcep-v01" / "monte_carlo_sensitivity.csv", index=False, encoding="utf-8-sig")

fig, ax = plt.subplots(figsize=(8.6, 5.4))
plot = sens_df.sort_values("top3_share", ascending=True)
ax.barh(plot["market"], plot["top3_share"] * 100,
        color=["#d28b26" if x >= 0.5 else "#4f79a7" for x in plot["top3_share"]])
for i, v in enumerate(plot["top3_share"] * 100):
    ax.text(v + 1, i, f"{v:.1f}%", va="center", fontsize=8)
ax.set_xlim(0, 105)
ax.set_xlabel("进入前三名的情景占比（%）")
ax.set_title("5000组权重情景下的前三稳定性")
ax.grid(axis="x", color="#d9dde2", lw=0.6, alpha=0.7)
fig.tight_layout()
fig.savefig(OUT / "ranking_sensitivity.pdf", bbox_inches="tight")
fig.savefig(OUT / "ranking_sensitivity.png", bbox_inches="tight", dpi=220)
plt.close(fig)

ranked[["country_name", "market", "score"]].sort_values("score", ascending=False).to_csv(
    ROOT / "sources" / "20260905-CHN-Roborock-HS85098090-rcep-v01" / "strategy_topsis_scores.csv",
    index=False, encoding="utf-8-sig")

print(ranked[["market", "score"]].sort_values("score", ascending=False).to_string(index=False))
print(sens_df[["market", "mean_rank", "top3_share"]].head(6).to_string(index=False))
