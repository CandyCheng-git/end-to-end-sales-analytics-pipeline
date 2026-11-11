with source as (
    select *
    from {{ source('bronze', 'olist_order_items') }}
),

typed as (
    select
        nullif(trim(order_id), '') as order_id,
        try_cast(order_item_id as integer) as order_item_id,
        nullif(trim(product_id), '') as product_id,
        nullif(trim(seller_id), '') as seller_id,
        try_cast(nullif(trim(shipping_limit_date), '') as timestamp) as shipping_limit_date,
        try_cast(price as decimal(18, 2)) as price,
        try_cast(freight_value as decimal(18, 2)) as freight_value
    from source
)

select
    concat(order_id, '|', cast(order_item_id as varchar)) as order_item_key,
    order_id,
    order_item_id,
    product_id,
    seller_id,
    shipping_limit_date,
    price,
    freight_value
from typed
