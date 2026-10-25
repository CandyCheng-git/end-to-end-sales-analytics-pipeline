select
    customer_id,
    max(customer_name) as customer_name
from {{ ref('stg_sales') }}
group by customer_id
