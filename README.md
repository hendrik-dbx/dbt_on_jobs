# dbt_on_jobs

A sample **dbt** project that builds a **silver → gold** warehouse aggregation
on Databricks, running entirely on **jobs compute** — no SQL warehouse.

It uses the **`dbt-spark`** adapter (not `dbt-databricks`) with the **`session`**
connection method, so dbt executes against the live `SparkSession` on the job
cluster and writes managed Delta tables into Unity Catalog.

## Layers

| Layer  | Schema   | Models |
| ------ | -------- | ------ |
| bronze | `bronze` | seeds: `raw_customers`, `raw_accounts`, `raw_transactions` |
| silver | `silver` | `silver_customers`, `silver_accounts`, `silver_transactions` — cleaned & conformed |
| gold   | `gold`   | `gold_daily_account_summary`, `gold_customer_monthly_summary`, `gold_category_spend` — warehouse aggregations |

The target Unity Catalog catalog is passed in as the **`catalog`** job parameter
(defaults to `hendrik_fsi`).

## How it runs on jobs compute (no warehouse)

- `profiles.yml` uses `type: spark`, `method: session`. On a Databricks job
  cluster a `SparkSession` already exists, so dbt reuses it — no Thrift server
  and no SQL warehouse.
- The Job runs a **notebook task** (`notebooks/run_dbt.py`) that invokes dbt
  **in-process** via `dbtRunner`, so the `session` method attaches to the live
  `SparkSession`. (The native Databricks `dbt` task can't do this — it shells
  dbt out to a fresh subprocess with no SparkSession, which fails session mode
  with `MASTER_URL_NOT_SET`.)
- The session method emits unqualified `schema.table`, so the notebook pins the
  default catalog via `USE CATALOG <catalog>` before running dbt.
- The task runs on an ephemeral single-node **job cluster** (DBR **16.4 LTS**)
  with `dbt-spark[session]` installed as a PyPI library.

## Serverless (work in progress)

A second job, `dbt_on_serverless_job`, targets serverless compute via a separate
notebook (`notebooks/run_dbt_serverless.py`) so the classic notebook stays clean.
Running the dbt-spark adapter on serverless is not yet working — the serverless
runtime ships **dbt Fusion** (no stable `spark` adapter) and its Spark Connect
endpoint is an in-process unix socket that vanilla `pyspark` won't accept. See
that notebook's header for the full findings and next steps.

## Deploy & run

Authenticate to the workspace first (profile `e2` →
`https://e2-demo-field-eng.cloud.databricks.com`):

```bash
databricks auth login --profile e2

databricks bundle validate -p e2
databricks bundle deploy   -p e2                 # deploys files + creates the Jobs
databricks bundle run dbt_on_jobs_job -p e2      # classic: seed → run → test  ✅
databricks bundle run dbt_on_serverless_job -p e2  # serverless: WIP
```

## Local layout

```
dbt_project.yml               # project config; silver/gold materialised as Delta tables
profiles.yml                  # dbt-spark session profiles (classic + serverless targets)
databricks.yml                # Asset Bundle: classic + serverless jobs
notebooks/run_dbt.py          # classic: invokes dbt in-process, reusing the SparkSession
notebooks/run_dbt_serverless.py  # serverless workarounds (WIP)
seeds/                        # raw FSI sample data (bronze)
models/silver/                # cleaned & conformed dimensions/facts
models/gold/                  # business-level warehouse aggregations
macros/                       # generate_schema_name override for clean schema names
```
