select
    sales_line_key,
    order_id,
    line_id,
    order_date,
    customer_id,
    product_id,
    quantity,
    unit_price,
    line_amount,
    order_status
from {{ ref('stg_sales') }}
