"""
FuMA Engine: AI & Rule-governed Taxonomy Classification, Attribute Extraction, and Multi-channel Description Formulas.
Owned by Member 2.
"""

from fuma_engine.schema import ProductRecord, AttributeItem
from fuma_engine.taxonomy_classifier import classify_taxonomy
from fuma_engine.attribute_extractor import extract_attributes
from fuma_engine.description_builder import build_all_descriptions
from fuma_engine.confidence_evaluator import evaluate_record
from fuma_engine.pipeline_interface import enrich_single_item, enrich_batch, enrich_dataframe
from fuma_engine.benchmark_metrics import calculate_benchmark_metrics

__version__ = "0.1.0"
__all__ = [
    "ProductRecord",
    "AttributeItem",
    "classify_taxonomy",
    "extract_attributes",
    "build_all_descriptions",
    "evaluate_record",
    "enrich_single_item",
    "enrich_batch",
    "enrich_dataframe",
    "calculate_benchmark_metrics"
]
