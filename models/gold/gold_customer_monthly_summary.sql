-- Gold: customer-level monthly warehouse aggregation.
-- Rolls the daily account summary up to (customer, month), enriched with
-- customer attributes — the kind of table that feeds BI dashboards.
with daily as (
    select * from {{ ref('gold_daily_account_summary') }}
),

customers as (
    select * from {{ ref('silver_customers') }}
)

select
    c.customer_id,
    c.first_name,
    c.last_name,
    c.segment,
    c.country,
    date_trunc('month', d.txn_date)        as month,
    count(distinct d.account_id)           as active_accounts,
    sum(d.txn_count)                       as txn_count,
    sum(d.total_credits)                   as total_credits,
    sum(d.total_debits)                    as total_debits,
    sum(d.net_amount)                      as net_amount
from daily d
inner join customers c
    on d.customer_id = c.customer_id
group by
    c.customer_id,
    c.first_name,
    c.last_name,
    c.segment,
    c.country,
    date_trunc('month', d.txn_date)
