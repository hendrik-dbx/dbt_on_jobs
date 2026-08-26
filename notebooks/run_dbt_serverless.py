# Databricks notebook source
# MAGIC %md
# MAGIC # Run dbt-spark on SERVERLESS compute — WORK IN PROGRESS
# MAGIC
# MAGIC Running the **dbt-spark** adapter on serverless is not straightforward.
# MAGIC What we've learned so far (see the classic notebook `run_dbt.py` for the
# MAGIC clean, working jobs-compute version):
# MAGIC
# MAGIC 1. The serverless runtime's dbt is **dbt Fusion** (`dbt-core 2.0.0-beta`),
# MAGIC    injected via site init so it shadows any pip install. Fusion's `spark`
# MAGIC    adapter is experimental and only speaks **TCP `sc://`**.
# MAGIC 2. Serverless exposes Spark Connect **only as an in-process unix socket**
# MAGIC    (`SPARK_REMOTE=unix:///databricks/sparkconnect/grpc.sock`).
# MAGIC 3. Vanilla PyPI `pyspark`'s Connect client **rejects `unix://`** — only
# MAGIC    Databricks' patched `pyspark` accepts it.
# MAGIC
# MAGIC Current workaround (still failing at the pyspark layer — TODO): pip-install
# MAGIC real Python `dbt-spark` into an isolated dir and run it in a subprocess
# MAGIC with `python -S` so the runtime's Fusion `dbt` is not on the path, using
# MAGIC the runtime's Databricks `pyspark` (unix-socket-capable) via PYTHONPATH.
# MAGIC
# MAGIC Next ideas to try: (A) shadow Fusion in-process and reuse the injected
# MAGIC `spark`; (B) point at the runtime pyspark (below); (E) find a Fusion
# MAGIC opt-out so the clean classic notebook works unchanged.

# COMMAND ----------

import os
import sys
import glob
import tempfile
import subprocess

dbutils.widgets.text("project_dir", "")
dbutils.widgets.text("catalog", "hendrik_fsi")
project_dir = dbutils.widgets.get("project_dir")
catalog = dbutils.widgets.get("catalog")
if project_dir and not os.path.exists(project_dir) and os.path.exists("/Workspace" + project_dir):
    project_dir = "/Workspace" + project_dir
if not project_dir or not os.path.exists(project_dir):
    raise ValueError(f"project_dir not found: {project_dir!r}")
print("Project dir:", project_dir, "| catalog:", catalog)

# The runtime's Databricks pyspark (handles the unix-socket SPARK_REMOTE).
import pyspark  # noqa: E402
PYSPARK_DIR = os.path.dirname(os.path.dirname(pyspark.__file__))
print("Databricks pyspark dir:", PYSPARK_DIR)

_scratch = tempfile.mkdtemp(prefix="dbt_on_jobs_")
common_args = [
    "--project-dir", project_dir,
    "--profiles-dir", project_dir,
    "--target", "databricks_serverless",
    "--target-path", os.path.join(_scratch, "target"),
    "--log-path", os.path.join(_scratch, "logs"),
    # TODO: catalog selection on the isolated subprocess connection still needs
    # wiring (candidate: an on-run-start hook using this var).
    "--vars", f'{{"catalog": "{catalog}"}}',
]
log_dir = os.path.join(_scratch, "logs")

# COMMAND ----------

# Install REAL Python dbt-spark (not Fusion) into an isolated dir. Pin dbt-core
# to a Python release from public PyPI (the serverless index resolves dbt-core
# to Fusion). No [session] extra, so no vanilla pyspark — we use the runtime's.
DBT_LIB = tempfile.mkdtemp(prefix="dbt_spark_lib_")
print("Installing dbt-spark into", DBT_LIB, "...")
_pip = subprocess.run(
    [sys.executable, "-m", "pip", "install", "--quiet", "--ignore-installed",
     "--index-url", "https://pypi.org/simple", "--target", DBT_LIB,
     "dbt-core>=1.8,<1.9", "dbt-spark>=1.8,<1.9",
     "pandas>=1.5", "pyarrow", "grpcio>=1.48.1", "grpcio-status>=1.48.1", "protobuf"],
    capture_output=True, text=True,
)
print(_pip.stdout[-2000:]); print(_pip.stderr[-2000:])
_pip.check_returncode()


def _tail_logs():
    chunks = []
    for path in sorted(glob.glob(os.path.join(log_dir, "*.log")) + glob.glob(os.path.join(log_dir, "*.jsonl"))):
        try:
            with open(path) as fh:
                chunks.append(f"--- {os.path.basename(path)} ---\n" + fh.read()[-4000:])
        except Exception as e:
            chunks.append(f"--- {path}: read error {e} ---")
    return "\n".join(chunks)


def run(command: str):
    env = dict(os.environ)
    # -S skips site init (no Fusion). PYTHONPATH = isolated Python dbt FIRST,
    # then the runtime's Databricks pyspark (unix-socket-capable). No Fusion dir.
    env["PYTHONPATH"] = DBT_LIB + os.pathsep + PYSPARK_DIR
    launcher = (
        "import sys, dbt; sys.stderr.write('dbt from: %r\\n' % list(getattr(dbt, '__path__', []))[:3]); "
        "from dbt.cli.main import dbtRunner; "
        "r = dbtRunner().invoke(sys.argv[1:]); "
        "sys.exit(0 if r.success else 1)"
    )
    p = subprocess.run(
        [sys.executable, "-S", "-c", launcher, command] + common_args,
        env=env, capture_output=True, text=True,
    )
    print(p.stdout[-4000:])
    if p.returncode != 0:
        raise RuntimeError(
            f"dbt {command} failed (rc={p.returncode})\nSTDERR:\n{p.stderr[-3000:]}\nLOGS:\n{_tail_logs()}"
        )


# COMMAND ----------

run("seed")

# COMMAND ----------

run("run")

# COMMAND ----------

run("test")

# COMMAND ----------

print("dbt seed / run / test completed successfully.")
