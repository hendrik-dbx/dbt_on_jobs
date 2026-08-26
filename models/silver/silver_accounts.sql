-- Silver: conformed account dimension. Only keeps active/closed accounts
-- with a valid owning customer.
with source as (
    select * from {{ ref('raw_accounts') }}
)

select
    cast(account_id as bigint)     as account_id,
    cast(customer_id as bigint)    as customer_id,
    lower(trim(account_type))      as account_type,
    upper(trim(currency))          as currency,
    cast(opened_date as date)      as opened_date,
    lower(trim(status))            as status
from source
where account_id is not null
  and customer_id is not null
