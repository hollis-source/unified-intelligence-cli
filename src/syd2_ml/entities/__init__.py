"""SYD2 ML Entities - Domain Models.

Core business entities for ML-based anomaly detection.
Immutable, framework-independent, pure Python.
"""

from .metric_features import MetricFeatures
from .anomaly import Anomaly, AnomalySeverity, AnomalyType
from .model_metadata import ModelMetadata, ModelType
from .training_data import TrainingDataset, DatasetStatistics

__all__ = [
    "MetricFeatures",
    "Anomaly",
    "AnomalySeverity",
    "AnomalyType",
    "ModelMetadata",
    "ModelType",
    "TrainingDataset",
    "DatasetStatistics",
]
