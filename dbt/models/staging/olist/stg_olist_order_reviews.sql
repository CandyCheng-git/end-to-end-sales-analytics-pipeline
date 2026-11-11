with source as (
    select *
    from {{ source('bronze', 'olist_order_reviews') }}
),

typed as (
    select
        nullif(trim(review_id), '') as review_id,
        nullif(trim(order_id), '') as order_id,
        try_cast(nullif(trim(review_score), '') as integer) as review_score,
        nullif(trim(review_comment_title), '') as review_comment_title,
        nullif(trim(review_comment_message), '') as review_comment_message,
        try_cast(nullif(trim(review_creation_date), '') as timestamp) as review_creation_date,
        try_cast(nullif(trim(review_answer_timestamp), '') as timestamp) as review_answer_timestamp
    from source
)

select
    concat(review_id, '|', order_id) as review_key,
    review_id,
    order_id,
    review_score,
    review_comment_title,
    review_comment_message,
    review_creation_date,
    review_answer_timestamp
from typed
