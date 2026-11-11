
{{ config(materialized='table') }}

with geolocation as (

    select *
    from {{ ref('stg_olist_geolocation') }}

),

aggregated as (

    select
        geolocation_zip_code_prefix,

        median(geolocation_lat)
            as median_latitude,

        median(geolocation_lng)
            as median_longitude,

        count(*) as observation_count

    from geolocation

    group by geolocation_zip_code_prefix

)

select *
from aggregated
