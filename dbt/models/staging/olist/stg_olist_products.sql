
with source as (

    select *
    from {{ source('bronze', 'olist_products') }}

),

typed as (

    select
        nullif(trim(product_id), '')
            as product_id,

        nullif(trim(product_category_name), '')
            as product_category_name,

        try_cast(
            nullif(trim(product_name_lenght), '')
            as integer
        ) as product_name_length,

        try_cast(
            nullif(trim(product_description_lenght), '')
            as integer
        ) as product_description_length,

        try_cast(
            nullif(trim(product_photos_qty), '')
            as integer
        ) as product_photos_qty,

        try_cast(
            nullif(trim(product_weight_g), '')
            as decimal(18, 2)
        ) as product_weight_g,

        try_cast(
            nullif(trim(product_length_cm), '')
            as decimal(18, 2)
        ) as product_length_cm,

        try_cast(
            nullif(trim(product_height_cm), '')
            as decimal(18, 2)
        ) as product_height_cm,

        try_cast(
            nullif(trim(product_width_cm), '')
            as decimal(18, 2)
        ) as product_width_cm

    from source

)

select *
from typed
