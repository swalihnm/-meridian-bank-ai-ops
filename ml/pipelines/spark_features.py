"""PySpark job: customer dispute-risk features, written to a Delta table (Week 7).

Same definitions as ml/risk/model.py build_features, written as Spark SQL. Output:
- data/processed/delta/customer_risk_features (Delta table, the deliverable)
- data/processed/spark/customer_risk_features.parquet (copy for the parity check on the host)

Run inside the Apache Spark container (see docs/LOG.md; Windows needs winutils for Hadoop, so the
job runs on Linux):
    docker run --rm -v "<repo>:/work" -w /work apache/spark:3.5.3 /opt/spark/bin/spark-submit \
      --packages io.delta:delta-spark_2.12:3.2.0 \
      --conf spark.sql.extensions=io.delta.sql.DeltaSparkSessionExtension \
      --conf spark.sql.catalog.spark_catalog=org.apache.spark.sql.delta.catalog.DeltaCatalog \
      --driver-memory 2g ml/pipelines/spark_features.py
"""

from __future__ import annotations

from pyspark.sql import Column, DataFrame, SparkSession
from pyspark.sql import functions as F

PROCESSED = "data/processed"
DELTA_OUT = f"{PROCESSED}/delta/customer_risk_features"
PARQUET_OUT = f"{PROCESSED}/spark/customer_risk_features.parquet"


def build(spark: SparkSession) -> DataFrame:
    customers = spark.read.parquet(f"{PROCESSED}/customers.parquet")
    accounts = spark.read.parquet(f"{PROCESSED}/accounts.parquet")
    txns = spark.read.parquet(f"{PROCESSED}/transactions.parquet")

    tx = txns.join(accounts.select("account_id", "customer_id"), on="account_id")
    tx = tx.withColumn("abs_amount", F.abs(F.col("amount_fils")).cast("double"))

    per_customer = tx.groupBy("customer_id").agg(
        F.count("*").alias("n_txn"),
        F.avg("abs_amount").alias("mean_abs_amount"),
        F.sum(F.when(F.col("category") == "online_retail", 1).otherwise(0)).alias("n_online"),
        F.sum(F.when(F.col("category") == "atm", 1).otherwise(0)).alias("n_atm"),
        F.sum(F.when(F.col("category") == "travel", 1).otherwise(0)).alias("n_travel"),
        F.sum(F.when(F.col("category") == "transfer_out", 1).otherwise(0)).alias("n_transfer"),
        F.sum(
            F.when(F.col("category") == "salary", F.col("amount_fils").cast("double")).otherwise(
                0.0
            )
        ).alias("income_total"),
    )

    accounts_per_customer = accounts.groupBy("customer_id").agg(F.count("*").alias("n_accounts"))

    feats = (
        customers.select("customer_id", F.col("segment"))
        .join(per_customer, on="customer_id", how="left")
        .join(accounts_per_customer, on="customer_id", how="left")
        .fillna(0)
    )

    def share(numerator: str) -> Column:
        return F.when(F.col("n_txn") > 0, F.col(numerator) / F.col("n_txn")).otherwise(0.0)

    return feats.select(
        "customer_id",
        F.col("n_accounts").cast("long"),
        F.col("n_txn").cast("long"),
        F.col("mean_abs_amount").cast("double"),
        share("n_online").alias("share_online"),
        share("n_atm").alias("share_atm"),
        share("n_travel").alias("share_travel"),
        share("n_transfer").alias("share_transfer_out"),
        F.col("income_total").cast("double"),
        (F.col("segment") == "affluent").cast("double").alias("segment_affluent"),
        (F.col("segment") == "business").cast("double").alias("segment_business"),
    )


def main() -> None:
    spark = (
        SparkSession.builder.appName("meridian-risk-features")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .getOrCreate()
    )
    features = build(spark)
    features.write.format("delta").mode("overwrite").save(DELTA_OUT)
    features.coalesce(1).write.mode("overwrite").parquet(PARQUET_OUT)
    print(f"SPARK_FEATURES_ROWS {spark.read.format('delta').load(DELTA_OUT).count()}")
    spark.stop()


if __name__ == "__main__":
    main()
