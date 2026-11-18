"""Generate the 6 dashboard charts. Run: python3 charts.py"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update({"figure.dpi": 150, "font.size": 10})
FOREST, OLIVE, TERRA, BROWN, SLATE, RED = (
    "#2F6B3A", "#606C38", "#C05A2E", "#7A4E2D", "#5D6D7E", "#B03A2E")
MONTH_LABEL = {"2025-01": "Jan", "2025-02": "Feb", "2025-03": "Mar",
               "2025-04": "Apr", "2025-05": "May", "2025-06": "Jun"}


def main():
    monthly = pd.read_csv("outputs/monthly_stockout_trend.csv")
    stores = pd.read_csv("outputs/stockouts_by_store.csv")
    turnover = pd.read_csv("outputs/turnover_by_category.csv")
    suppliers = pd.read_csv("outputs/supplier_performance.csv")
    excess = pd.read_csv("outputs/excess_by_category.csv")

    # 1) Monthly stock-out rate trend
    fig, ax = plt.subplots(figsize=(8, 4))
    labels = [MONTH_LABEL[m] for m in monthly["month"]]
    ax.plot(labels, monthly["stockout_rate_pct"], color=TERRA, lw=2.5,
            marker="o", markersize=7, markerfacecolor=FOREST,
            markeredgecolor=FOREST)
    for x, y in zip(labels, monthly["stockout_rate_pct"]):
        ax.text(x, y + 0.12, f"{y:.2f}%", ha="center", fontsize=9)
    ax.set_ylabel("Stock-out rate (% of SKU-store-days)")
    ax.set_ylim(0, monthly["stockout_rate_pct"].max() * 1.25)
    ax.set_title("Stock-Outs Rise as Opening Stock Burns Off — "
                 "Then Follow the Delivery Cycle")
    fig.tight_layout(); fig.savefig("images/monthly_stockout_trend.png")
    plt.close(fig)

    # 2) Stock-out rate by store (worst store in alert red)
    s = stores.sort_values("stockout_rate_pct")
    colors = [RED if v == s["stockout_rate_pct"].max() else FOREST
              for v in s["stockout_rate_pct"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(s["store_id"], s["stockout_rate_pct"], color=colors)
    for _, r in s.iterrows():
        ax.text(r["stockout_rate_pct"] + 0.05, r["store_id"],
                f"{r['stockout_rate_pct']:.2f}%  "
                f"({int(r['stockout_days'])} days)", va="center",
                fontsize=9)
    ax.set_xlabel("Stock-out rate (% of SKU-store-days)")
    ax.set_xlim(0, s["stockout_rate_pct"].max() * 1.45)
    ax.set_title("Stock-Out Rate by Store —\nBusiest Store (ST05) Runs Out Most")
    fig.tight_layout(); fig.savefig("images/stockout_rate_by_store.png")
    plt.close(fig)

    # 3) Annualised inventory turnover by category
    t = turnover.sort_values("turnover_annualised")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(t["category"], t["turnover_annualised"], color=OLIVE)
    for _, r in t.iterrows():
        ax.text(r["turnover_annualised"] + 0.15, r["category"],
                f"{r['turnover_annualised']:.2f}x  "
                f"({r['days_of_supply']:.0f} days of supply)",
                va="center", fontsize=9)
    ax.set_xlabel("Inventory turnover (times per year, annualised)")
    ax.set_xlim(0, t["turnover_annualised"].max() * 1.5)
    ax.set_title("Inventory Turnover by Category —\nAccessories Fastest, Appliances Slowest")
    fig.tight_layout(); fig.savefig("images/turnover_by_category.png")
    plt.close(fig)

    # 4) Supplier on-time delivery % (worst in alert red)
    sup = suppliers.sort_values("on_time_pct")
    colors = [RED if v < 60 else SLATE if v < 78 else FOREST
              for v in sup["on_time_pct"]]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    ax.barh(sup["supplier_name"] + " (" + sup["supplier_id"] + ")",
            sup["on_time_pct"], color=colors)
    for _, r in sup.iterrows():
        ax.text(r["on_time_pct"] + 1.5,
                r["supplier_name"] + " (" + r["supplier_id"] + ")",
                f"{r['on_time_pct']:.1f}%", va="center", fontsize=9)
    ax.set_xlabel("Deliveries on or before the promised date (%)")
    ax.set_xlim(0, 100)
    ax.set_title("Supplier On-Time Delivery —\nTwo Suppliers Are Late Half the Time")
    fig.tight_layout(); fig.savefig("images/supplier_on_time.png")
    plt.close(fig)

    # 5) Lead time: promised vs actual by supplier
    sup2 = suppliers.sort_values("avg_lead_actual_days")
    y = range(len(sup2))
    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    ax.barh([i + 0.2 for i in y], sup2["avg_lead_promised_days"],
            height=0.4, color=SLATE, label="Promised")
    ax.barh([i - 0.2 for i in y], sup2["avg_lead_actual_days"],
            height=0.4, color=TERRA, label="Actual")
    ax.set_yticks(list(y))
    ax.set_yticklabels(sup2["supplier_name"] + " (" + sup2["supplier_id"]
                       + ")", fontsize=9)
    ax.set_xlabel("Average lead time (days)")
    ax.legend(fontsize=9)
    ax.set_title("Lead Time: Promised vs Actual —\nImports Run Longest and Slip Most")
    fig.tight_layout(); fig.savefig("images/lead_time_promised_vs_actual.png")
    plt.close(fig)

    # 6) Excess inventory value by category (final day, >60 days of supply)
    e = excess.sort_values("excess_value_usd")
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(e["category"], e["excess_value_usd"], color=BROWN)
    for _, r in e.iterrows():
        ax.text(r["excess_value_usd"] + 18000, r["category"],
                f"${r['excess_value_usd']:,.0f}", va="center", fontsize=9)
    ax.set_xlabel("Excess inventory value at cost (USD, final day)")
    ax.set_xlim(0, e["excess_value_usd"].max() * 1.28)
    ax.set_title("Excess Inventory by Category —\nBig-Ticket TVs and Laptops Hold the Cash")
    fig.tight_layout()
    fig.savefig("images/excess_inventory_by_category.png")
    plt.close(fig)
    print("Wrote 6 charts to images/")


if __name__ == "__main__":
    main()
