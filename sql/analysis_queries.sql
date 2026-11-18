-- Inventory & Supply Chain Analytics — SQL analysis queries
-- (SQLite/Postgres-compatible) Portfolio project, synthetic data.
-- Tables:
--   daily_inventory (date, store_id, sku, on_hand_start, units_received,
--                    units_sold, on_hand_end)   -- one row per SKU-store-day
--   products        (sku, name, category, supplier_id, unit_cost,
--                    unit_price, reorder_point, lead_time_days_promised)
--   purchase_orders (po_id, sku, store_id, supplier_id, order_date,
--                    qty_ordered, promised_date, received_date, qty_received)
--   suppliers       (supplier_id, supplier_name)
--   stores          (store_id, city, state)
-- A "stock-out day" = a SKU-store-day with on_hand_start + units_received = 0
-- (the shelf was empty for the whole day).

-- Q1. Overall in-stock / stock-out rate for the 180 days
SELECT COUNT(*)                                          AS sku_store_days,
       SUM(CASE WHEN on_hand_start + units_received = 0
                THEN 1 ELSE 0 END)                       AS stockout_days,
       ROUND(100.0 * SUM(CASE WHEN on_hand_start + units_received = 0
                              THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                         AS stockout_rate_pct,
       ROUND(100.0 - 100.0 * SUM(CASE WHEN on_hand_start
                              + units_received = 0 THEN 1 ELSE 0 END)
             / COUNT(*), 2)                              AS instock_rate_pct
FROM daily_inventory;

-- Q2. Stock-out rate by store — which stores run out most?
SELECT store_id,
       COUNT(*)                                          AS sku_store_days,
       SUM(CASE WHEN on_hand_start + units_received = 0
                THEN 1 ELSE 0 END)                       AS stockout_days,
       ROUND(100.0 * SUM(CASE WHEN on_hand_start + units_received = 0
                              THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                         AS stockout_rate_pct,
       SUM(units_sold)                                   AS units_sold
FROM daily_inventory
GROUP BY store_id
ORDER BY stockout_rate_pct DESC;

-- Q3. Monthly stock-out trend
SELECT strftime('%Y-%m', date)                           AS month,
       COUNT(*)                                          AS sku_store_days,
       SUM(CASE WHEN on_hand_start + units_received = 0
                THEN 1 ELSE 0 END)                       AS stockout_days,
       ROUND(100.0 * SUM(CASE WHEN on_hand_start + units_received = 0
                              THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                         AS stockout_rate_pct
FROM daily_inventory
GROUP BY month
ORDER BY month;

-- Q4. Inventory turnover and days of supply by category
--     turnover = COGS / average daily inventory value (x 365/180 to
--     annualise); days of supply = avg units on hand / avg daily sold
WITH daily_cat AS (
    SELECT d.date, p.category,
           SUM(d.units_sold * p.unit_cost)               AS cogs_day,
           SUM(d.on_hand_end * p.unit_cost)              AS inv_value_day,
           SUM(d.on_hand_end)                            AS units_on_hand_day,
           SUM(d.units_sold)                             AS units_sold_day
    FROM daily_inventory d
    JOIN products p ON p.sku = d.sku
    GROUP BY d.date, p.category
)
SELECT category,
       ROUND(SUM(cogs_day), 2)                           AS cogs_usd,
       ROUND(AVG(inv_value_day), 2)                      AS avg_inventory_value_usd,
       ROUND(SUM(cogs_day) / AVG(inv_value_day), 2)      AS turnover_period,
       ROUND(SUM(cogs_day) / AVG(inv_value_day) * 365.0
             / COUNT(DISTINCT date), 2)                  AS turnover_annualised,
       ROUND(AVG(units_on_hand_day)
             / (SUM(units_sold_day) / COUNT(DISTINCT date)), 1)
                                                         AS days_of_supply
FROM daily_cat
GROUP BY category
ORDER BY turnover_annualised DESC;

-- Q5. Supplier scorecard: lead time promised vs actual, on-time %
--     (received orders only; on-time = received on/before promised date)
SELECT po.supplier_id, s.supplier_name,
       COUNT(*)                                          AS orders_received,
       ROUND(AVG(julianday(po.promised_date)
                 - julianday(po.order_date)), 2)         AS avg_promised_days,
       ROUND(AVG(julianday(po.received_date)
                 - julianday(po.order_date)), 2)         AS avg_actual_days,
       ROUND(100.0 * SUM(CASE WHEN po.received_date <= po.promised_date
                              THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                         AS on_time_pct,
       ROUND(AVG(CASE WHEN po.received_date > po.promised_date
                      THEN julianday(po.received_date)
                           - julianday(po.promised_date) END), 2)
                                                         AS avg_days_late,
       ROUND(100.0 * SUM(po.qty_received)
             / SUM(po.qty_ordered), 2)                   AS qty_fill_pct
FROM purchase_orders po
JOIN suppliers s ON s.supplier_id = po.supplier_id
WHERE po.received_date IS NOT NULL AND po.received_date <> ''
GROUP BY po.supplier_id, s.supplier_name
ORDER BY on_time_pct;

-- Q6. Top stock-out SKUs (empty-shelf days across all 5 stores)
SELECT d.sku, p.name, p.category, p.supplier_id,
       SUM(CASE WHEN d.on_hand_start + d.units_received = 0
                THEN 1 ELSE 0 END)                       AS stockout_days,
       ROUND(100.0 * SUM(CASE WHEN d.on_hand_start + d.units_received = 0
                              THEN 1 ELSE 0 END) / COUNT(*), 2)
                                                         AS stockout_rate_pct
FROM daily_inventory d
JOIN products p ON p.sku = d.sku
GROUP BY d.sku, p.name, p.category, p.supplier_id
ORDER BY stockout_days DESC
LIMIT 10;

-- Q7. Late-order detail: how late is late? (distribution of days late)
SELECT CASE WHEN days_late BETWEEN 1 AND 2 THEN '1-2 days'
            WHEN days_late BETWEEN 3 AND 5 THEN '3-5 days'
            WHEN days_late BETWEEN 6 AND 9 THEN '6-9 days'
            ELSE '10+ days' END                          AS lateness_band,
       COUNT(*)                                          AS late_orders
FROM (SELECT julianday(received_date) - julianday(promised_date)
             AS days_late
      FROM purchase_orders
      WHERE received_date IS NOT NULL AND received_date <> ''
        AND received_date > promised_date)
GROUP BY lateness_band
ORDER BY MIN(days_late);

-- Q8. Orders still in transit at the end of the window, by supplier
SELECT supplier_id, COUNT(*)                             AS open_orders,
       SUM(qty_ordered)                                  AS units_in_transit
FROM purchase_orders
WHERE received_date IS NULL OR received_date = ''
GROUP BY supplier_id
ORDER BY open_orders DESC;

-- Q9. Excess inventory on the final day: units above 60 days of supply
--     for that SKU at that store, valued at unit cost
WITH avg_daily AS (
    SELECT store_id, sku, AVG(units_sold * 1.0)          AS avg_daily_sold
    FROM daily_inventory
    WHERE on_hand_start + units_received > 0
    GROUP BY store_id, sku
),
final_day AS (
    SELECT * FROM daily_inventory
    WHERE date = (SELECT MAX(date) FROM daily_inventory)
)
SELECT p.category,
       ROUND(SUM(MAX(f.on_hand_end - 60 * a.avg_daily_sold, 0)), 1)
                                                         AS excess_units,
       ROUND(SUM(MAX(f.on_hand_end - 60 * a.avg_daily_sold, 0)
                 * p.unit_cost), 2)                      AS excess_value_usd
FROM final_day f
JOIN avg_daily a ON a.store_id = f.store_id AND a.sku = f.sku
JOIN products p ON p.sku = f.sku
GROUP BY p.category
ORDER BY excess_value_usd DESC;

-- Q10. Estimated lost sales from empty shelves: each stock-out day is
--      valued at the SKU's average daily units sold at that store
--      (on in-stock days) x unit price. Counts full empty days only,
--      so it understates the true loss.
WITH avg_daily AS (
    SELECT store_id, sku, AVG(units_sold * 1.0)          AS avg_daily_sold
    FROM daily_inventory
    WHERE on_hand_start + units_received > 0
    GROUP BY store_id, sku
)
SELECT COUNT(*)                                          AS stockout_days,
       ROUND(SUM(a.avg_daily_sold), 1)                   AS est_lost_units,
       ROUND(SUM(a.avg_daily_sold * p.unit_price), 2)    AS est_lost_sales_usd
FROM daily_inventory d
JOIN avg_daily a ON a.store_id = d.store_id AND a.sku = d.sku
JOIN products p ON p.sku = d.sku
WHERE d.on_hand_start + d.units_received = 0;
