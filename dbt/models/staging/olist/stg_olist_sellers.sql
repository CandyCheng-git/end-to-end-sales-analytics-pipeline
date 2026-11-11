
with source as (

    select *
    from {{ source('bronze', 'olist_sellers') }}

),

cleaned as (

    select
        nullif(trim(seller_id), '')
            as seller_id,

        -- Keep ZIP prefix as text to preserve leading zeros
        nullif(trim(seller_zip_code_prefix), '')
            as seller_zip_code_prefix,

        lower(nullif(trim(seller_city), ''))
            as seller_city,

        upper(nullif(trim(seller_state), ''))
            as seller_state

    from source

)

select *
from cleaned
