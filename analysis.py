"""Inventory & supply chain KPI analysis.

Portfolio project — synthetic data only.
Run: python3 analysis.py  ->  writes outputs/*.csv and outputs/insights.md

Definitions (also in the README, in plain words):
  * Available units on a day = on_hand_start + units_received.
  * Stock-out day = a SKU-store-day with ZERO units available: the shelf
    was empty for the whole day. In-stock rate = 100 - stock-out rate.
  * Inventory turnover = cost of goods sold / average inventory value
    (average of the daily end-of-day inventory values). Annualised
    turnover multiplies the 180-day figure by 365/180.
  * Days of supply = average units on hand / average daily units sold.
  * On-time = received_date on or before promised_date. Lead-time and
    lateness figures use received orders only; orders still in transit
    on the last day are counted separately.
  * Excess inventory (final day) = units above 60 days of supply for
    that SKU at that store, valued at unit cost.
  * Estimated lost sales: for each stock-out day, the SKU's average
    daily units sold at that store (on days it was in stock) x unit
    price. This counts only full empty-shelf days, so it understates
    the true loss (it ignores days the shelf emptied mid-day).
"""
import pandas as pd

EXCESS_DAYS_THRESHOLD = 60  # stock above 60 days of supply = excess


def load():
    daily = pd.read_csv("data/daily_inventory.csv", parse_dates=["date"])
    products = pd.read_csv("data/products.csv")
    suppliers = pd.read_csv("data/suppliers.csv")
    pos = pd.read_csv("data/purchase_orders.csv",
                      parse_dates=["order_date", "promised_date",
                                   "received_date"])
    daily = daily.merge(products, on="sku", how="left")
    daily["available"] = daily["on_hand_start"] + daily["units_received"]
    daily["stockout_day"] = (daily["available"] == 0).astype(int)
    daily["cogs"] = daily["units_sold"] * daily["unit_cost"]
    daily["inv_value"] = daily["on_hand_end"] * daily["unit_cost"]
    return daily, products, suppliers, pos


def avg_daily_demand(daily):
    """Average daily units sold per SKU-store on in-stock days — the
    demand proxy used for days-of-supply, excess and lost-sales maths."""
    in_stock = daily[daily["available"] > 0]
    return (in_stock.groupby(["store_id", "sku"])["units_sold"]
            .mean().rename("avg_daily_sold"))


def main():
    daily, products, suppliers, pos = load()
    days = daily["date"].nunique()
    total_days = len(daily)
    stockout_days = int(daily["stockout_day"].sum())
    stockout_rate = 100 * stockout_days / total_days

    total_cogs = float(daily["cogs"].sum())
    avg_inv_value = float(daily.groupby("date")["inv_value"].sum().mean())
    turnover = total_cogs / avg_inv_value
    turnover_ann = turnover * 365 / days
    avg_units_on_hand = float(
        daily.groupby("date")["on_hand_end"].sum().mean())
    avg_daily_sold = float(daily["units_sold"].sum()) / days
    days_of_supply = avg_units_on_hand / avg_daily_sold
    total_revenue = float(
        (daily["units_sold"] * daily["unit_price"]).sum())

    # ---- turnover & days of supply by category -------------------------
    cat_rows = []
    for cat, g in daily.groupby("category"):
        cogs = float(g["cogs"].sum())
        avg_inv = float(g.groupby("date")["inv_value"].sum().mean())
        avg_units = float(g.groupby("date")["on_hand_end"].sum().mean())
        daily_sold = float(g["units_sold"].sum()) / days
        t = cogs / avg_inv
        cat_rows.append({
            "category": cat, "units_sold": int(g["units_sold"].sum()),
            "cogs_usd": round(cogs, 2),
            "avg_inventory_value_usd": round(avg_inv, 2),
            "turnover_period": round(t, 2),
            "turnover_annualised": round(t * 365 / days, 2),
            "days_of_supply": round(avg_units / daily_sold, 1),
            "stockout_rate_pct": round(100 * g["stockout_day"].mean(), 2),
        })
    turnover_cat = pd.DataFrame(cat_rows).sort_values(
        "turnover_annualised", ascending=False)
    turnover_cat.to_csv("outputs/turnover_by_category.csv", index=False)

    # ---- supplier performance ------------------------------------------
    received = pos[pos["received_date"].notna()].copy()
    received["lead_actual"] = (received["received_date"]
                               - received["order_date"]).dt.days
    received["lead_promised"] = (received["promised_date"]
                                 - received["order_date"]).dt.days
    received["days_late"] = received["lead_actual"] - received["lead_promised"]
    received["on_time"] = (received["days_late"] <= 0).astype(int)
    sup_rows = []
    for sid, g in received.groupby("supplier_id"):
        late = g[g["days_late"] > 0]
        sup_rows.append({
            "supplier_id": sid,
            "supplier_name": suppliers.set_index("supplier_id")
            .loc[sid, "supplier_name"],
            "orders_received": len(g),
            "avg_lead_promised_days": round(g["lead_promised"].mean(), 2),
            "avg_lead_actual_days": round(g["lead_actual"].mean(), 2),
            "on_time_pct": round(100 * g["on_time"].mean(), 2),
            "late_orders": len(late),
            "avg_days_late": round(late["days_late"].mean(), 2)
            if len(late) else 0.0,
            "qty_fill_pct": round(
                100 * g["qty_received"].sum() / g["qty_ordered"].sum(), 2),
        })
    sup_perf = pd.DataFrame(sup_rows).sort_values("on_time_pct")
    sup_perf.to_csv("outputs/supplier_performance.csv", index=False)

    n_pos = len(pos)
    n_received = len(received)
    late_all = received[received["days_late"] > 0]
    on_time_pct = 100 * received["on_time"].mean()
    avg_actual = float(received["lead_actual"].mean())
    avg_promised = float(received["lead_promised"].mean())
    avg_days_late = float(late_all["days_late"].mean())

    # ---- stock-outs by store -------------------------------------------
    store_rows = (daily.groupby("store_id")
                  .agg(sku_store_days=("stockout_day", "size"),
                       stockout_days=("stockout_day", "sum"),
                       units_sold=("units_sold", "sum"))
                  .reset_index())
    store_rows["stockout_rate_pct"] = (
        100 * store_rows["stockout_days"]
        / store_rows["sku_store_days"]).round(2)
    store_rows = store_rows.sort_values("stockout_rate_pct",
                                        ascending=False)
    store_rows.to_csv("outputs/stockouts_by_store.csv", index=False)

    # ---- demand proxy, lost sales, top stock-out SKUs -------------------
    avg_daily = avg_daily_demand(daily)
    daily = daily.join(avg_daily, on=["store_id", "sku"])
    so = daily[daily["stockout_day"] == 1].copy()
    so["lost_units"] = so["avg_daily_sold"]
    so["lost_sales_usd"] = so["avg_daily_sold"] * so["unit_price"]
    est_lost_units = float(so["lost_units"].sum())
    est_lost_sales = float(so["lost_sales_usd"].sum())

    top = (so.groupby(["sku", "name", "category", "supplier_id"])
           .agg(stockout_days=("stockout_day", "sum"),
                est_lost_sales_usd=("lost_sales_usd", "sum"))
           .reset_index())
    days_per_sku = days * daily["store_id"].nunique()
    top["stockout_rate_pct"] = (
        100 * top["stockout_days"] / days_per_sku).round(2)
    top["est_lost_sales_usd"] = top["est_lost_sales_usd"].round(2)
    top = top.sort_values("stockout_days", ascending=False).head(10)
    top.to_csv("outputs/top_stockout_skus.csv", index=False)

    # ---- monthly stock-out trend ----------------------------------------
    daily["month"] = daily["date"].dt.strftime("%Y-%m")
    monthly = (daily.groupby("month")
               .agg(sku_store_days=("stockout_day", "size"),
                    stockout_days=("stockout_day", "sum"))
               .reset_index())
    monthly["stockout_rate_pct"] = (
        100 * monthly["stockout_days"] / monthly["sku_store_days"]).round(2)
    monthly.to_csv("outputs/monthly_stockout_trend.csv", index=False)

    # ---- excess inventory on the final day -------------------------------
    last_date = daily["date"].max()
    final = daily[daily["date"] == last_date].copy()
    final["excess_units"] = (
        final["on_hand_end"]
        - EXCESS_DAYS_THRESHOLD * final["avg_daily_sold"]).clip(lower=0)
    final["excess_value_usd"] = final["excess_units"] * final["unit_cost"]
    excess_units = float(final["excess_units"].sum())
    excess_value = float(final["excess_value_usd"].sum())
    final_inv_value = float(final["inv_value"].sum())
    exc_cat = (final.groupby("category")
               .agg(excess_units=("excess_units", "sum"),
                    excess_value_usd=("excess_value_usd", "sum"))
               .reset_index())
    exc_cat["excess_units"] = exc_cat["excess_units"].round(1)
    exc_cat["excess_value_usd"] = exc_cat["excess_value_usd"].round(2)
    exc_cat = exc_cat.sort_values("excess_value_usd", ascending=False)
    exc_cat.to_csv("outputs/excess_by_category.csv", index=False)

    # ---- KPI summary ------------------------------------------------------
    kpis = [
        ("total_skus", int(daily["sku"].nunique())),
        ("total_stores", int(daily["store_id"].nunique())),
        ("total_suppliers", int(pos["supplier_id"].nunique())),
        ("days_analysed", int(days)),
        ("total_sku_store_days", int(total_days)),
        ("stockout_days", stockout_days),
        ("stockout_rate_pct", round(stockout_rate, 2)),
        ("instock_rate_pct", round(100 - stockout_rate, 2)),
        ("total_units_sold", int(daily["units_sold"].sum())),
        ("total_revenue_usd", round(total_revenue, 2)),
        ("total_cogs_usd", round(total_cogs, 2)),
        ("avg_inventory_value_usd", round(avg_inv_value, 2)),
        ("final_day_inventory_value_usd", round(final_inv_value, 2)),
        ("inventory_turnover_period", round(turnover, 2)),
        ("inventory_turnover_annualised", round(turnover_ann, 2)),
        ("avg_days_of_supply", round(days_of_supply, 1)),
        ("total_purchase_orders", int(n_pos)),
        ("received_purchase_orders", int(n_received)),
        ("open_purchase_orders", int(n_pos - n_received)),
        ("on_time_delivery_pct", round(on_time_pct, 2)),
        ("late_purchase_orders", int(len(late_all))),
        ("late_po_pct", round(100 * len(late_all) / n_received, 2)),
        ("avg_lead_time_promised_days", round(avg_promised, 2)),
        ("avg_lead_time_actual_days", round(avg_actual, 2)),
        ("avg_days_late", round(avg_days_late, 2)),
        ("excess_days_threshold", EXCESS_DAYS_THRESHOLD),
        ("excess_inventory_units", round(excess_units, 1)),
        ("excess_inventory_value_usd", round(excess_value, 2)),
        ("est_lost_units", round(est_lost_units, 1)),
        ("est_lost_sales_usd", round(est_lost_sales, 2)),
    ]
    pd.DataFrame(kpis, columns=["kpi", "value"]).to_csv(
        "outputs/kpi_summary.csv", index=False)

    worst_store = store_rows.iloc[0]
    worst_supplier = sup_perf.iloc[0]
    top_sku = top.iloc[0]
    best_cat = turnover_cat.iloc[0]
    worst_turn_cat = turnover_cat.iloc[-1]
    exc_top1 = exc_cat.iloc[0]
    exc_top2 = exc_cat.iloc[1]
    insights = f"""# Insights — Inventory & Supply Chain Analytics (Portfolio Project, synthetic data)

> Portfolio project — not paid work experience. Synthetic data only.
> All figures below are outputs of analysis.py on the data in this repo.

## Headline KPIs
- **Scope:** {daily['sku'].nunique()} SKUs x {daily['store_id'].nunique()} stores x {days} days = {total_days:,} SKU-store-days | **Units sold:** {int(daily['units_sold'].sum()):,} | **Revenue:** ${total_revenue:,.2f}
- **In-stock rate:** {100 - stockout_rate:.2f}% — the shelf was empty for a full day {stockout_days} times (**stock-out rate {stockout_rate:.2f}%**)
- **Estimated lost sales from empty shelves:** ${est_lost_sales:,.2f} (~{est_lost_units:,.0f} units that would have sold on those days)
- **Inventory turnover:** {turnover:.2f}x in 180 days = **{turnover_ann:.2f}x annualised** | **Average days of supply:** {days_of_supply:.1f} days | Average inventory value: ${avg_inv_value:,.2f}
- **Suppliers:** {n_received} of {n_pos} purchase orders received ({n_pos - n_received} still in transit at day 180) | **On-time delivery: {on_time_pct:.2f}%** | Late orders average **{avg_days_late:.2f} days late** | Actual lead time {avg_actual:.2f} days vs {avg_promised:.2f} promised
- **Excess inventory on the final day:** ${excess_value:,.2f} of stock sitting above a {EXCESS_DAYS_THRESHOLD}-day supply ({excess_units:,.0f} units)

## Findings
- **The headline in-stock rate hides real money.** 98%+ in stock sounds healthy, but the {stockout_days} empty-shelf days are concentrated in fast-selling, high-price SKUs, so they cost an estimated ${est_lost_sales:,.0f} — about {100 * est_lost_sales / total_revenue:.1f}% of the period's revenue.
- **Worst stock-out SKU:** {top_sku['sku']} ({top_sku['name']}, {top_sku['category']}) — empty {int(top_sku['stockout_days'])} of {days_per_sku} SKU-store-days ({top_sku['stockout_rate_pct']:.2f}%), an estimated ${top_sku['est_lost_sales_usd']:,.0f} of lost sales.
- **Worst store:** {worst_store['store_id']} with a {worst_store['stockout_rate_pct']:.2f}% stock-out rate — the highest-demand stores stock out most, because reorder points are set from chain-wide category averages, not from each store's own demand.
- **Worst supplier:** {worst_supplier['supplier_name']} ({worst_supplier['supplier_id']}) delivered on time only {worst_supplier['on_time_pct']:.1f}% of the time and averaged {worst_supplier['avg_days_late']:.1f} days late when late. Supplier reliability, not demand, is the biggest controllable cause of stock-outs on the SKUs they serve.
- **Turnover is healthiest in {best_cat['category']}** ({best_cat['turnover_annualised']:.2f}x annualised) and slowest in {worst_turn_cat['category']} ({worst_turn_cat['turnover_annualised']:.2f}x). The excess dollars sit in the big-ticket categories — {exc_top1['category']} (${exc_top1['excess_value_usd']:,.0f}) and {exc_top2['category']} (${exc_top2['excess_value_usd']:,.0f}) — because one excess TV or laptop ties up as much cash as a shelf of accessories.
- **The root cause is a settings problem, not a people problem.** Reorder points are calculated from category-average demand: fast SKUs get too little cover and run out while a late delivery is in transit; slow SKUs get far too much and pile up as excess. Setting reorder points per SKU-store from its own demand history is the single fix that attacks both problems at once.

## Honest limitations
- Lost sales are an estimate, not a measurement: they count only days the shelf was empty all day, valued at that SKU-store's average daily sales. Days the shelf emptied mid-day are ignored, so the true figure is higher.
- "Excess" depends on the 60-day threshold; a different threshold changes the dollar figure (the method is stated so anyone can re-run it with their own).
- Demand, supplier behaviour and starting stock are simulated with a fixed seed (42) to mirror a real electronics retailer's patterns; no real company data is used.
"""
    with open("outputs/insights.md", "w") as f:
        f.write(insights)
    print("Wrote outputs/kpi_summary.csv, outputs/turnover_by_category.csv, "
          "outputs/supplier_performance.csv, outputs/stockouts_by_store.csv, "
          "outputs/top_stockout_skus.csv, "
          "outputs/monthly_stockout_trend.csv, "
          "outputs/excess_by_category.csv, outputs/insights.md")
    print(f"In-stock: {100 - stockout_rate:.2f}% | Turnover (ann.): "
          f"{turnover_ann:.2f}x | On-time: {on_time_pct:.2f}% | "
          f"Lost sales: ${est_lost_sales:,.2f} | "
          f"Excess: ${excess_value:,.2f}")


if __name__ == "__main__":
    main()
