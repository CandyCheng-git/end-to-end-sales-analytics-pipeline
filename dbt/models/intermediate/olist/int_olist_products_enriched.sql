with products as (
    select *
    from {{ ref('stg_olist_products') }}
),

translations as (
    select *
    from {{ ref('stg_olist_category_name_translation') }}
)

select
    p.*,
    t.product_category_name_english,
    case
        when p.product_category_name is null then 'missing_source_category'
        when t.product_category_name is null then 'unmapped_translation'
        else 'translated'
    end as category_mapping_status
from products p
left join translations t
    on lower(p.product_category_name) = t.product_category_name
