import json
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ValidationError, model_validator


class RelationType(str, Enum):
    ONE_TO_MANY = "one-to-many"
    MANY_TO_MANY = "many-to-many"


ALLOWED_RELATION_FIELDS = {"parent"}


class Relation(BaseModel, frozen=True):
    type: RelationType
    field: str | None = None

    @model_validator(mode="after")
    def validate_relation(self) -> "Relation":
        if self.type == RelationType.ONE_TO_MANY:
            if not self.field:
                raise ValueError("one-to-many relation requires 'field'")
            if self.field not in ALLOWED_RELATION_FIELDS:
                raise ValueError(
                    f"unknown field '{self.field}', must be one of {ALLOWED_RELATION_FIELDS}" # SQLI protection
                )
        return self


class Rule(BaseModel, frozen=True):
    tag: str
    source_entity: str
    destination_entity: str
    relation: Relation

    @property
    def label(self) -> str:
        return f"{self.source_entity}:{self.tag}->{self.destination_entity}"


class RulesFile(BaseModel):
    rules: list[Rule]


def load_rules(path: Path) -> list[Rule]:
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}") from e

    try:
        return RulesFile.model_validate(data).rules
    except ValidationError as e:
        raise ValueError(f"Invalid rules in {path}: {e}") from e
