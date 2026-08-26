-- Silver: conformed customer dimension.
-- Cleans and types the raw seed, normalises text fields.
with source as (
    select * from {{ ref('raw_customers') }}
)

select
    cast(customer_id as bigint)              as customer_id,
    initcap(trim(first_name))                as first_name,
    initcap(trim(last_name))                 as last_name,
    lower(trim(email))                       as email,
    cast(signup_date as date)                as signup_date,
    lower(trim(segment))                     as segment,
    upper(trim(country))                     as country
from source
where customer_id is not null
