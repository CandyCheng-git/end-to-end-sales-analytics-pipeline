with source as (
    select *
    from {{ source('bronze', 'olist_order_payments') }}
),

typed as (
    select
        nullif(trim(order_id), '') as order_id,
        try_cast(nullif(trim(payment_sequential), '') as integer) as payment_sequential,
        lower(nullif(trim(payment_type), '')) as payment_type,
        try_cast(nullif(trim(payment_installments), '') as integer) as payment_installments,
        try_cast(nullif(trim(payment_value), '') as decimal(18, 2)) as payment_value
    from source
)

select
    concat(order_id, '|', cast(payment_sequential as varchar)) as order_payment_key,
    order_id,
    payment_sequential,
    payment_type,
    payment_installments,
    payment_value
from typed
