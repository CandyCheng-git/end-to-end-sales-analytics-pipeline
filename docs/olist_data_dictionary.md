# Olist E-Commerce — Source Data Dictionary

**Milestone:** M1 — Source Understanding
**Data source:** [Olist Brazilian E-Commerce Public Dataset (Kaggle)](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
**Status:** M1 source dictionary verified for **all 9 original CSV filenames and all 52 column names in order** against the downloaded files using Docker/Pandas on 2026-10-26. Row counts, candidate keys and selected relationship checks were profiled locally on 2026-10-25. Field descriptions are interpretations of the source, not independently verified business contracts.

## Source table inventory and intended grain

| CSV | Rows verified | Columns verified | Grain / candidate key |
| --- | ---: | ---: | --- |
| `olist_orders_dataset.csv` | 99,441 | 8 | One order / `order_id` |
| `olist_order_items_dataset.csv` | 112,650 | 7 | One item within order / (`order_id`, `order_item_id`) |
| `olist_order_payments_dataset.csv` | 103,886 | 5 | One payment sequence within order / (`order_id`, `payment_sequential`) |
| `olist_order_reviews_dataset.csv` | 99,224 | 7 | One review/order association / observed unique (`review_id`, `order_id`) |
| `olist_customers_dataset.csv` | 99,441 | 5 | One order-linked customer record / `customer_id` |
| `olist_products_dataset.csv` | 32,951 | 9 | One product / `product_id` |
| `olist_sellers_dataset.csv` | 3,095 | 4 | One seller / `seller_id` |
| `olist_geolocation_dataset.csv` | 1,000,163 | 5 | Source geolocation observations; **ZIP prefix is not unique** |
| `product_category_name_translation.csv` | 71 | 2 | One source category mapping / `product_category_name` |

## Expected source fields and interpretation

*All 52 field names and ordering were checked against the actual local CSV headers. Preserve original source spelling, including `lenght`, rather than silently renaming upstream raw columns.*

### Orders — 8 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `order_id` | Order identifier; candidate key, unique in profiled snapshot |
| `customer_id` | Order-linked customer row; joins to Customers |
| `order_status` | Business workflow state (`delivered`, `canceled`, etc.) |
| `order_purchase_timestamp` | Purchase event timestamp |
| `order_approved_at` | Approval timestamp, potentially missing |
| `order_delivered_carrier_date` | Handoff-to-carrier timestamp, potentially missing |
| `order_delivered_customer_date` | Actual customer delivery timestamp, missing in 2,965 rows |
| `order_estimated_delivery_date` | Original estimated delivery timestamp |

### Order items — 7 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `order_id` | Parent order identifier |
| `order_item_id` | Item sequence number within order; not globally unique |
| `product_id` | Product key |
| `seller_id` | Seller key |
| `shipping_limit_date` | Seller shipping deadline |
| `price` | Item price (BRL), excluding separately recorded freight |
| `freight_value` | Freight value (BRL) |

### Payments — 5 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `order_id` | Parent order identifier |
| `payment_sequential` | Payment sequence number within order |
| `payment_type` | Payment method |
| `payment_installments` | Payment instalment count |
| `payment_value` | Recorded payment amount (BRL); **not equivalent to profit** |

### Reviews — 7 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `review_id` | Review identifier; **not unique by itself** |
| `order_id` | Order related to review; **not unique by itself** |
| `review_score` | Review score |
| `review_comment_title` | Optional review headline; 87,656 missing |
| `review_comment_message` | Optional review text; 58,247 missing |
| `review_creation_date` | Review creation date |
| `review_answer_timestamp` | Review answer timestamp |

**Validated review-grain evidence:** 789 repeated Review IDs across multiple orders; 814 extra rows beyond first ID; 547 orders with multiple review rows; 0 duplicate (`review_id`, `order_id`) pairs; 0 fully duplicated rows. Retain all records and validate the pair as an observed candidate key.

### Customers — 5 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `customer_id` | Order-linked customer key; joins to Orders |
| `customer_unique_id` | Person-level customer identifier; use for repeat-customer analysis |
| `customer_zip_code_prefix` | Postal code prefix; retain as text |
| `customer_city` | Customer city |
| `customer_state` | Customer state |

### Products — 9 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `product_id` | Product key |
| `product_category_name` | Source Portuguese category; 2 distinct values not mapped in translation table |
| `product_name_lenght` | Source product name character length; typo appears in source naming |
| `product_description_lenght` | Source product description character length; typo appears in source naming |
| `product_photos_qty` | Product photo quantity |
| `product_weight_g` | Weight in grams |
| `product_length_cm` | Length in centimetres |
| `product_height_cm` | Height in centimetres |
| `product_width_cm` | Width in centimetres |

**Missing translation impact:** `pc_gamer` (3 products), `portateis_cozinha_e_preparadores_de_alimentos` (10 products). Preserve the source category and document translation fallbacks.

### Sellers — 4 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `seller_id` | Seller key |
| `seller_zip_code_prefix` | Postal prefix as text |
| `seller_city` | Seller city |
| `seller_state` | Seller state |

### Geolocation — 5 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `geolocation_zip_code_prefix` | Repeating postal prefix; **not a primary key** |
| `geolocation_lat` | Latitude |
| `geolocation_lng` | Longitude |
| `geolocation_city` | City |
| `geolocation_state` | State |

For a customer or seller postal-prefix join, first produce an explicitly grained derived mapping; do not directly join raw geolocation to fact rows.

### Category name translation — 2 fields

| Field | Source meaning / suggested treatment |
| --- | --- |
| `product_category_name` | Portuguese category; profiled unique candidate key |
| `product_category_name_english` | English category name |

## Validated candidate relationships

| Child key | Parent key | Unmatched non-null distinct child keys |
| --- | --- | ---: |
| `orders.customer_id` | `customers.customer_id` | 0 |
| `order_items.order_id` | `orders.order_id` | 0 |
| `order_items.product_id` | `products.product_id` | 0 |
| `order_items.seller_id` | `sellers.seller_id` | 0 |
| `payments.order_id` | `orders.order_id` | 0 |
| `reviews.order_id` | `orders.order_id` | 0 |
| `products.product_category_name` | `category_translation.product_category_name` | 2 |

## Modelling and data-quality guardrails for later milestones

1. **Protect grain:** Order items, payments and reviews can each have multiple rows per order; do not join them naively and sum amounts.
2. **Customer identity:** `customer_id` and `customer_unique_id` have different meanings; define person-level KPIs on the latter.
3. **Money:** Define item GMV, freight and payments separately; payment amount is not profit or necessarily item GMV.
4. **Missing dates:** Interpret missing delivery timestamp alongside order status; eight delivered orders lack it and six canceled orders have one.
5. **Preserve exceptions:** Keep unmatched category values and source review rows; create explicit exception flags/marts as appropriate.
6. **Validate candidate keys:** Observed uniqueness is based on one source snapshot, not a guarantee for future loads.

## Re-run local header verification

Run this command from the project root to compare the expected columns above with the actual downloaded CSV header values:

```powershell
docker compose run --rm pipeline python -c "from pathlib import Path; import pandas as pd; root=Path('/app/data/raw/olist'); [(print(p.name + ': ' + ', '.join(pd.read_csv(p, nrows=0).columns))) for p in sorted(root.glob('*.csv'))]"
```

The local verification matched **9/9 CSV headers and 52/52 column names in the same order**. The authoritative per-column missing values remain in local `data/processed/olist/olist_column_nulls.csv`. If the source snapshot changes, rerun this check and update the dictionary as necessary. The script, documentation and ignore rules were merged via PR #1.