"""
Pydantic models for a client's scoring framework YAML
(clients/<client_id>/scoring/<framework_id>.yaml). Validated at load time so a
malformed config fails loudly and specifically, not with a KeyError deep in
the scoring pipeline.

Nothing in this module names a real dimension, client, or framework — those
all come from the YAML file loaded at runtime.
"""
from pydantic import BaseModel, Field, model_validator


class RubricBand(BaseModel):
    min_score: int
    max_score: int
    label: str
    description: str


class RagThresholds(BaseModel):
    # A dimension score <= red_max is Red, <= amber_max is Amber, else Green.
    red_max: int
    amber_max: int


class Dimension(BaseModel):
    id: str
    name: str
    description: str
    weight: float = Field(gt=0)
    rubric: list[RubricBand]
    rag_thresholds: RagThresholds


class ScoringScale(BaseModel):
    min: int = 1
    max: int = 10


class ScoringConfig(BaseModel):
    id: str
    version: str
    name: str
    scale: ScoringScale
    dimensions: list[Dimension]
    cta_text: str

    @model_validator(mode="after")
    def _dimensions_not_empty(self) -> "ScoringConfig":
        if not self.dimensions:
            raise ValueError("A scoring config needs at least one dimension.")
        ids = [d.id for d in self.dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Duplicate dimension ids in config {self.id!r}: {ids}")
        return self

    def overall_score(self, dimension_scores: dict[str, int]) -> float:
        """Weighted average of per-dimension scores, normalised to 0-100."""
        total_weight = sum(d.weight for d in self.dimensions)
        weighted_sum = sum(dimension_scores[d.id] * d.weight for d in self.dimensions)
        raw_avg = weighted_sum / total_weight
        span = self.scale.max - self.scale.min
        return round((raw_avg - self.scale.min) / span * 100, 1) if span else 0.0

    def rag_band(self, dimension_id: str, score: int) -> str:
        thresholds = next(d for d in self.dimensions if d.id == dimension_id).rag_thresholds
        if score <= thresholds.red_max:
            return "red"
        if score <= thresholds.amber_max:
            return "amber"
        return "green"
