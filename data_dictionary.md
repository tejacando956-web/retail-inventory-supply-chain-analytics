# Data Dictionary — Inventory & Supply Chain Analytics (synthetic data)

## data/products.csv — one row per SKU (40)

| Column | Type | Description |
|---|---|---|
| sku | string | Unique product ID (`SKU001`…`SKU040`). |
| name | string | Product name, e.g. `TV Model 3`. |
| category | string | TVs, Laptops, Audio, Appliances, Accessories. |
| supplier_id | string | The supplier this SKU is ordered from (`SUP01`…`SUP08`). |
| unit_cost | float | What the retailer pays per unit, USD. |
| unit_price | float | Shelf price per unit, USD. |
| reorder_point | int | When a store's stock of this SKU falls to this many units, a new order is placed. Set from the **category-average** demand — see "planted behaviour" below. |
| lead_time_days_promised | int | Days the supplier promises between order and delivery for this SKU. |

## data/stores.csv — the 5 stores

| Column | Type | Description |
|---|---|---|
| store_id | string | `ST01`…`ST05`. |
| city / state | string | Store location. ST05 (Denver) is the highest-demand store; ST01 (Dallas) the quietest. |

## data/suppliers.csv — the 8 suppliers

| Column | Type | Description |
|---|---|---|
| supplier_id | string | `SUP01`…`SUP08`. |
| supplier_name | string | Distributor name. Reliability is NOT stored here — it is measured from `purchase_orders.csv`. |

## data/daily_inventory.csv — one row per SKU × store × day (36,000)

| Column | Type | Description |
|---|---|---|
| date | date | 2025-01-01 … 2025-06-29 (180 days). |
| store_id | string | Store. |
| sku | string | Product. |
| on_hand_start | int | Units on the shelf at the start of the day. |
| units_received | int | Units delivered that day (from purchase orders arriving). |
| units_sold | int | Units sold that day. Capped by what was on the shelf — demand above the shelf count is lost, not recorded. |
| on_hand_end | int | Units left at day end = on_hand_start + units_received − units_sold. |

**Available units** on a day = `on_hand_start + units_received`. A **stock-out day** is a row where available units = 0 (the shelf was empty all day).

## data/purchase_orders.csv — one row per replenishment order (383)

| Column | Type | Description |
|---|---|---|
| po_id | string | Unique order ID (`PO-0001`…). |
| sku / store_id | string | What was ordered, and for which store. |
| supplier_id | string | The SKU's supplier. |
| order_date | date | Day the order was placed (the day stock hit the reorder point). |
| qty_ordered | int | Units ordered (roughly one replenishment cycle of cover). |
| promised_date | date | order_date + the SKU's promised lead time. |
| received_date | date | Actual delivery date. **Blank if the order was still in transit on 2025-06-29** (23 orders). |
| qty_received | int | Units actually delivered. 0 while in transit; less than qty_ordered on partial shipments (the two least reliable suppliers). |

## Planted behaviour (by design, so the analysis has something real to find)

- Demand varies by category, store size, SKU popularity and weekday (weekends sell more). Four SKUs are planted **slow movers** and four are **fast sellers**.
- **Reorder points are set from category-average demand**, not from each SKU's own demand — the classic real-world settings flaw. Fast SKUs therefore get too little cover and run out while deliveries are in transit; slow SKUs get too much and pile up as excess stock.
- Each supplier has a hidden reliability profile: QuickShip Logistics (SUP04) and PrimeSource Wholesale (SUP02) are dependable; GlobalTech Imports (SUP05) has long lead times and slips often; BudgetParts Wholesale (SUP08) is late on about half its orders and sometimes ships short quantities.

## outputs/

| File | Contents |
|---|---|
| kpi_summary.csv | Headline KPIs: scope, in-stock / stock-out rates, units sold, revenue, COGS, average inventory value, turnover (180-day and annualised), days of supply, purchase-order counts, on-time %, average lead times and lateness, excess inventory (units and $ above a 60-day supply on the final day), estimated lost sales ($ and units). |
| turnover_by_category.csv | Units sold, COGS, average inventory value, turnover, days of supply and stock-out rate per category. |
| supplier_performance.csv | Per supplier: orders received, promised vs actual lead time, on-time %, late orders, average days late, quantity fill %. |
| stockouts_by_store.csv | SKU-store-days, stock-out days, stock-out rate % and units sold per store. |
| top_stockout_skus.csv | Top 10 SKUs by stock-out days, with category, supplier, stock-out rate % and estimated lost sales $. |
| monthly_stockout_trend.csv | Stock-out days and rate % by month. |
| excess_by_category.csv | Excess units and excess value $ per category (final day, 60-day threshold). |
| insights.md | Narrative findings and honest limitations. |

## Key definitions (analysis.py)

| Measure | Definition |
|---|---|
| In-stock rate | % of SKU-store-days with available units > 0. Stock-out rate = 100 − in-stock rate. |
| Inventory turnover | COGS ÷ average inventory value (mean of daily end-of-day inventory values). Annualised = 180-day turnover × 365/180. |
| Days of supply | Average units on hand ÷ average daily units sold. |
| On-time delivery | received_date ≤ promised_date, over received orders only. |
| Average days late | Mean of (actual − promised lead time) over **late** orders only. |
| Excess inventory | On the final day, units above 60 × the SKU-store's average daily units sold (in-stock days), valued at unit cost. |
| Estimated lost sales | For each stock-out day: the SKU-store's average daily units sold (in-stock days) × unit price. Full empty days only — understates the true loss. |
