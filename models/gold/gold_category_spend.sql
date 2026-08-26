-- Gold: spend-by-category aggregation across all customers.
-- Debits only (actual spend), summarised by segment + category.
with txn as (
    select * from {{ ref('silver_transactions') }}
),

accounts as (
    select * from {{ ref('silver_accounts') }}
),

customers as (
    select * from {{ ref('silver_customers') }}
)

select
    c.segment,
    t.category,
    t.currency,
    count(*)               as txn_count,
    sum(t.abs_amount)      as total_spend,
    avg(t.abs_amount)      as avg_spend
from txn t
inner join accounts a  on t.account_id = a.account_id
inner join customers c on a.customer_id = c.customer_id
where t.direction = 'debit'
group by
    c.segment,
    t.category,
    t.currency
