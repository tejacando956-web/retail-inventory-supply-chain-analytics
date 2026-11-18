# Insights — Inventory & Supply Chain Analytics (Portfolio Project, synthetic data)

> Portfolio project — not paid work experience. Synthetic data only.
> All figures below are outputs of analysis.py on the data in this repo.

## Headline KPIs
- **Scope:** 40 SKUs x 5 stores x 180 days = 36,000 SKU-store-days | **Units sold:** 88,804 | **Revenue:** $40,672,163.84
- **In-stock rate:** 98.59% — the shelf was empty for a full day 508 times (**stock-out rate 1.41%**)
- **Estimated lost sales from empty shelves:** $1,086,952.52 (~1,610 units that would have sold on those days)
- **Inventory turnover:** 3.87x in 180 days = **7.85x annualised** | **Average days of supply:** 45.4 days | Average inventory value: $5,579,076.18
- **Suppliers:** 360 of 383 purchase orders received (23 still in transit at day 180) | **On-time delivery: 71.94%** | Late orders average **3.70 days late** | Actual lead time 9.56 days vs 8.55 promised
- **Excess inventory on the final day:** $1,593,825.74 of stock sitting above a 60-day supply (3,641 units)

## Findings
- **The headline in-stock rate hides real money.** 98%+ in stock sounds healthy, but the 508 empty-shelf days are concentrated in fast-selling, high-price SKUs, so they cost an estimated $1,086,953 — about 2.7% of the period's revenue.
- **Worst stock-out SKU:** SKU003 (TV Model 3, TVs) — empty 79 of 900 SKU-store-days (8.78%), an estimated $296,601 of lost sales.
- **Worst store:** ST05 with a 1.86% stock-out rate — the highest-demand stores stock out most, because reorder points are set from chain-wide category averages, not from each store's own demand.
- **Worst supplier:** BudgetParts Wholesale (SUP08) delivered on time only 48.3% of the time and averaged 5.8 days late when late. Supplier reliability, not demand, is the biggest controllable cause of stock-outs on the SKUs they serve.
- **Turnover is healthiest in Accessories** (8.46x annualised) and slowest in Appliances (7.49x). The excess dollars sit in the big-ticket categories — TVs ($618,852) and Laptops ($601,120) — because one excess TV or laptop ties up as much cash as a shelf of accessories.
- **The root cause is a settings problem, not a people problem.** Reorder points are calculated from category-average demand: fast SKUs get too little cover and run out while a late delivery is in transit; slow SKUs get far too much and pile up as excess. Setting reorder points per SKU-store from its own demand history is the single fix that attacks both problems at once.

## Honest limitations
- Lost sales are an estimate, not a measurement: they count only days the shelf was empty all day, valued at that SKU-store's average daily sales. Days the shelf emptied mid-day are ignored, so the true figure is higher.
- "Excess" depends on the 60-day threshold; a different threshold changes the dollar figure (the method is stated so anyone can re-run it with their own).
- Demand, supplier behaviour and starting stock are simulated with a fixed seed (42) to mirror a real electronics retailer's patterns; no real company data is used.
