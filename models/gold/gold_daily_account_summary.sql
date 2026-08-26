-- Gold: daily aggregation of transaction activity per account.
-- One row per (account, day) — the core warehouse fact aggregation.
with txn as (
    select * from {{ ref('silver_transactions') }}
),

accounts as (
    select * from {{ ref('silver_accounts') }}
)

select
    t.account_id,
    a.customer_id,
    a.account_type,
    t.currency,
    t.txn_date,
    count(*)                                                    as txn_count,
    sum(case when t.direction = 'credit' then t.abs_amount else 0 end) as total_credits,
    sum(case when t.direction = 'debit'  then t.abs_amount else 0 end) as total_debits,
    sum(t.amount)                                               as net_amount,
    avg(t.abs_amount)                                           as avg_txn_size
from txn t
inner join accounts a
    on t.account_id = a.account_id
group by
    t.account_id,
    a.customer_id,
    a.account_type,
    t.currency,
    t.txn_date
