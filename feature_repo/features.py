"""Feast definitions for the customer dispute-risk features.

Must match FEATURES in ml/risk/model.py.
"""

from datetime import timedelta

from feast import Entity, FeatureView, Field, FileSource
from feast.types import Float32, Int64
from feast.value_type import ValueType

# The join key is declared as a string explicitly. Without this, Feast infers a JSON type from the
# Parquet source and fails to materialise.
customer = Entity(name="customer", join_keys=["customer_id"], value_type=ValueType.STRING)

risk_source = FileSource(
    path="../data/processed/feast/customer_risk_features.parquet",
    timestamp_field="event_timestamp",
)

customer_risk_features = FeatureView(
    name="customer_risk_features",
    entities=[customer],
    ttl=timedelta(days=3650),
    schema=[
        Field(name="n_accounts", dtype=Int64),
        Field(name="n_txn", dtype=Int64),
        Field(name="mean_abs_amount", dtype=Float32),
        Field(name="share_online", dtype=Float32),
        Field(name="share_atm", dtype=Float32),
        Field(name="share_travel", dtype=Float32),
        Field(name="share_transfer_out", dtype=Float32),
        Field(name="income_total", dtype=Float32),
        Field(name="segment_affluent", dtype=Float32),
        Field(name="segment_business", dtype=Float32),
    ],
    source=risk_source,
)
