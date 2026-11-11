with source as (
    select *
    from {{ source('bronze', 'olist_customers') }}
),

cleaned as (
    select
        nullif(trim(customer_id), '') as customer_id,
        nullif(trim(customer_unique_id), '') as customer_unique_id,
        -- Keep ZIP prefixes as strings to preserve leading zeros.
        nullif(trim(customer_zip_code_prefix), '') as customer_zip_code_prefix,
        lower(nullif(trim(customer_city), '')) as customer_city,
        upper(nullif(trim(customer_state), '')) as customer_state
    from source
)

select *
from cleaned
