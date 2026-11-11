
with source as (

    select *
    from {{ source('bronze', 'olist_geolocation') }}

),

typed as (

    select
        -- Preserve leading zeros
        nullif(
            trim(geolocation_zip_code_prefix), ''
        ) as geolocation_zip_code_prefix,

        try_cast(
            nullif(trim(geolocation_lat), '')
            as double
        ) as geolocation_lat,

        try_cast(
            nullif(trim(geolocation_lng), '')
            as double
        ) as geolocation_lng,

        lower(
            nullif(trim(geolocation_city), '')
        ) as geolocation_city,

        upper(
            nullif(trim(geolocation_state), '')
        ) as geolocation_state

    from source

)

select *
from typed
