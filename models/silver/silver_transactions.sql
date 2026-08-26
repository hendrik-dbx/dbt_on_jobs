-- Silver: conformed transaction fact.
-- Types the timestamp, derives the transaction date and debit/credit split
-- used by the gold aggregations.
with source as (
    select * from {{ ref('raw_transactions') }}
)

select
    cast(transaction_id as bigint)                 as transaction_id,
    cast(account_id as bigint)                     as account_id,
    cast(txn_ts as timestamp)                      as txn_ts,
    cast(txn_ts as date)                           as txn_date,
    cast(amount as decimal(18, 2))                 as amount,
    case when amount >= 0 then 'credit' else 'debit' end as direction,
    abs(cast(amount as decimal(18, 2)))            as abs_amount,
    upper(trim(currency))                          as currency,
    lower(trim(category))                          as category,
    trim(merchant)                                 as merchant
from source
where transaction_id is not null
  and account_id is not null
