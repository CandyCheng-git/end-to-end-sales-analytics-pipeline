select
    product_id,
    max(product_name) as product_name
from {{ ref('stg_sales') }}
group by product_id
