select
    order_date,
    count(distinct order_id) as completed_orders,
    sum(quantity) as units_sold,
    cast(sum(line_amount) as decimal(18, 2)) as gross_sales
from {{ ref('fct_sales') }}
where order_status = 'Completed'
group by order_date
