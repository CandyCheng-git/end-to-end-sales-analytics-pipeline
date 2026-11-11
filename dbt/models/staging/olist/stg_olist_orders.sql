with source as (
    select *
    from {{ source('bronze', 'olist_orders') }}
),

typed as (
    select
        nullif(trim(order_id), '') as order_id,
        nullif(trim(customer_id), '') as customer_id,
        lower(nullif(trim(order_status), '')) as order_status,
        try_cast(nullif(trim(order_purchase_timestamp), '') as timestamp) as order_purchase_timestamp,
        try_cast(nullif(trim(order_approved_at), '') as timestamp) as order_approved_at,
        try_cast(nullif(trim(order_delivered_carrier_date), '') as timestamp) as order_delivered_carrier_date,
        try_cast(nullif(trim(order_delivered_customer_date), '') as timestamp) as order_delivered_customer_date,
        try_cast(nullif(trim(order_estimated_delivery_date), '') as timestamp) as order_estimated_delivery_date
    from source
)

select *
from typed
