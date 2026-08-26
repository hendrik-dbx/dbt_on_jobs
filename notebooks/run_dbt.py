# Databricks notebook source
# MAGIC %md
# MAGIC # Run dbt-spark on jobs compute
# MAGIC
# MAGIC Invokes dbt **in-process** via `dbtRunner` using dbt-spark's `session`
# MAGIC method, so dbt reuses the job cluster's live `SparkSession`. No SQL
# MAGIC warehouse is involved.
# MAGIC
# MAGIC Parameters:
# MAGIC - `project_dir` — the deployed dbt project dir (`${workspace.file_path}`).
# MAGIC - `catalog` — the Unity Catalog catalog to write into.

# COMMAND ----------

import os
import tempfile
from dbt.cli.main import dbtRunner, dbtRunnerResult

# COMMAND ----------

dbutils.widgets.text("project_dir", "")
dbutils.widgets.text("catalog", "hendrik_fsi")
project_dir = dbutils.widgets.get("project_dir")
catalog = dbutils.widgets.get("catalog")

if project_dir and not os.path.exists(project_dir) and os.path.exists("/Workspace" + project_dir):
    project_dir = "/Workspace" + project_dir
if not project_dir or not os.path.exists(project_dir):
    raise ValueError(f"project_dir not found: {project_dir!r}")

# dbt-spark's session method emits unqualified `schema.table`, so it ignores the
# profile `catalog`. Pin the default catalog on the reused SparkSession instead.
spark.sql(f"USE CATALOG {catalog}")
print("Project dir:", project_dir, "| catalog:", spark.sql("SELECT current_catalog()").first()[0])

# Keep dbt's writable output off the read-only workspace mount.
_scratch = tempfile.mkdtemp(prefix="dbt_on_jobs_")
common_args = [
    "--project-dir", project_dir,
    "--profiles-dir", project_dir,
    "--target", "databricks_jobs",
    "--target-path", os.path.join(_scratch, "target"),
    "--log-path", os.path.join(_scratch, "logs"),
]

dbt = dbtRunner()


def run(command: str):
    res: dbtRunnerResult = dbt.invoke([command] + common_args)
    if not res.success:
        details = []
        if res.exception is not None:
            details.append(f"exception: {res.exception}")
        for r in getattr(getattr(res, "result", None), "results", []) or []:
            if str(getattr(r, "status", "")).lower() not in ("success", "pass"):
                node = getattr(r, "node", None)
                name = getattr(node, "name", None) or getattr(r, "unique_id", "node")
                details.append(f"{name}: {getattr(r, 'status', '?')}: {getattr(r, 'message', '')}")
        raise RuntimeError(f"dbt {command} failed:\n" + "\n".join(details or ["see logs above"]))


# COMMAND ----------

run("seed")

# COMMAND ----------

run("run")

# COMMAND ----------

run("test")

# COMMAND ----------

print("dbt seed / run / test completed successfully.")
