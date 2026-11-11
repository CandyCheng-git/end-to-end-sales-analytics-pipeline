with source as (
    select *
    from {{ source('bronze', 'olist_category_name_translation') }}
),

cleaned as (
    select
        lower(nullif(trim(product_category_name), '')) as product_category_name,
        nullif(trim(product_category_name_english), '') as product_category_name_english
    from source
)

select *
from cleaned
