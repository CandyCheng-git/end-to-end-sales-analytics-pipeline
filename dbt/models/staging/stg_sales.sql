with ranked as (
    select
        trim(order_id) as order_id,
        trim(line_id) as line_id,
        cast(order_date as date) as order_date,
        trim(customer_id) as customer_id,
        trim(customer_name) as customer_name,
        trim(product_id) as product_id,
        trim(product_name) as product_name,
        cast(quantity as integer) as quantity,
        cast(unit_price as decimal(18, 2)) as unit_price,
        trim(order_status) as order_status,
        cast(source_updated_at as timestamp) as source_updated_at,
        row_number() over (
            partition by trim(order_id), trim(line_id)
            order by cast(source_updated_at as timestamp) desc
        ) as row_version
    from {{ source('bronze', 'raw_sales') }}
)
select
    order_id || '-' || line_id as sales_line_key,
    order_id, line_id, order_date,
    customer_id, customer_name,
    product_id, product_name,
    quantity, unit_price, order_status, source_updated_at,
    cast(quantity * unit_price as decimal(18, 2)) as line_amount
from ranked
where row_version = 1
