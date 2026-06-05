from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SourceRef(StrictModel):
    document: str
    page: int | None = None
    section: str | None = None
    quote: str | None = None
    notes: str | None = None


class CourseStatus(StrEnum):
    completed = "completed"
    in_progress = "in_progress"
    planned = "planned"


class CourseSource(StrEnum):
    nus = "NUS"
    sep = "SEP"
    apc = "APC"
    exemption = "EXEMPTION"
    manual = "MANUAL"


class ApprovalStatus(StrEnum):
    approved = "approved"
    pending = "pending"
    rejected = "rejected"
    unknown = "unknown"


class AllocationRole(StrEnum):
    primary = "primary"
    double_count = "double_count"
    residual_ue = "residual_ue"
    ignored = "ignored"


class CourseAttempt(StrictModel):
    course_code: str
    title: str | None = None
    units: int = 4
    term: str | None = None
    grade: str | None = None
    su: bool = False
    status: CourseStatus = CourseStatus.completed
    source: CourseSource = CourseSource.nus
    mapped_to: str | None = None
    approval_status: ApprovalStatus = ApprovalStatus.approved
    topic_tags: list[str] = Field(default_factory=list)
    approved_for: list[str] = Field(default_factory=list)

    @field_validator("course_code", "mapped_to")
    @classmethod
    def normalize_course_code(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value

    @property
    def effective_code(self) -> str:
        return self.mapped_to or self.course_code


class CourseAlias(StrictModel):
    id: str
    alias: str
    canonical: str
    description: str | None = None
    source_ref: SourceRef | None = None
    override: bool = False


class CoursePool(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    includes: list[str] = Field(default_factory=list)
    excludes: list[str] = Field(default_factory=list)
    override: bool = False

    @field_validator("includes", "excludes")
    @classmethod
    def normalize_patterns(cls, value: list[str]) -> list[str]:
        return [item.upper().strip() for item in value]


class Requirement(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    requirement_type: Literal[
        "course_list",
        "choice",
        "pool_count",
        "all_of",
        "choose_count",
        "choose_units",
        "project_option",
    ]
    courses: list[str] = Field(default_factory=list)
    pool_id: str | None = None
    min_count: int | None = None
    units: int | None = None
    topic_tags: list[str] = Field(default_factory=list)
    override: bool = False

    @field_validator("courses")
    @classmethod
    def normalize_courses(cls, value: list[str]) -> list[str]:
        return [item.upper().strip() for item in value]


class RequirementGroup(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    requirement_ids: list[str] = Field(default_factory=list)
    override: bool = False


class SpecialisationPath(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    requirement_ids: list[str] = Field(default_factory=list)
    activation_flags: list[str] = Field(default_factory=list)


class Specialisation(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    total_units: int = 20
    max_overlap_units: int = 8
    min_distinct_units: int = 12
    requirement_ids: list[str] = Field(default_factory=list)
    course_pool_ids: list[str] = Field(default_factory=list)
    paths: list[SpecialisationPath] = Field(default_factory=list)
    notes: str | None = None
    override: bool = False


class Constraint(StrictModel):
    id: str
    description: str
    source_ref: SourceRef
    constraint_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    override: bool = False


class Allocation(StrictModel):
    course_code: str
    requirement_id: str
    units: int = 4
    allocation_role: AllocationRole = AllocationRole.primary
    manual: bool = False
    notes: str | None = None

    @field_validator("course_code")
    @classmethod
    def normalize_course(cls, value: str) -> str:
        return value.upper().strip()


class ConstraintResult(StrictModel):
    constraint_id: str
    passed: bool
    description: str
    source_ref: SourceRef | None = None
    message: str
    affected_courses: list[str] = Field(default_factory=list)


class SpecialisationResult(StrictModel):
    specialisation_id: str
    status: Literal["PASS", "FAIL", "PARTIAL"]
    selected_path_id: str | None = None
    units_counted: int = 0
    overlap_units: int = 0
    distinct_units: int = 0
    satisfied_requirements: list[str] = Field(default_factory=list)
    failed_requirements: list[str] = Field(default_factory=list)
    messages: list[str] = Field(default_factory=list)


class AuditResult(StrictModel):
    overall_status: Literal["PASS", "FAIL", "PARTIAL"]
    requirement_statuses: dict[str, Literal["PASS", "FAIL", "PARTIAL"]] = Field(default_factory=dict)
    satisfied_requirements: list[str] = Field(default_factory=list)
    failed_requirements: list[str] = Field(default_factory=list)
    allocations: list[Allocation] = Field(default_factory=list)
    constraint_results: list[ConstraintResult] = Field(default_factory=list)
    specialisation_results: list[SpecialisationResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DegreeAuditConfig(StrictModel):
    programme_id: str | None = None
    title: str | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    requirement_groups: list[RequirementGroup] = Field(default_factory=list)
    course_pools: list[CoursePool] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    specialisations: list[Specialisation] = Field(default_factory=list)
    course_aliases: list[CourseAlias] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_referenced_ids(self) -> "DegreeAuditConfig":
        pools = {pool.id for pool in self.course_pools}
        requirements = {requirement.id for requirement in self.requirements}
        for requirement in self.requirements:
            if requirement.pool_id and requirement.pool_id not in pools:
                raise ValueError(f"Requirement {requirement.id} references unknown pool {requirement.pool_id}")
        for group in self.requirement_groups:
            for requirement_id in group.requirement_ids:
                if requirement_id not in requirements:
                    raise ValueError(f"Requirement group {group.id} references unknown requirement {requirement_id}")
        for specialisation in self.specialisations:
            for pool_id in specialisation.course_pool_ids:
                if pool_id not in pools:
                    raise ValueError(f"Specialisation {specialisation.id} references unknown pool {pool_id}")
            for requirement_id in specialisation.requirement_ids:
                if requirement_id not in requirements:
                    raise ValueError(f"Specialisation {specialisation.id} references unknown requirement {requirement_id}")
            for path in specialisation.paths:
                for requirement_id in path.requirement_ids:
                    if requirement_id not in requirements:
                        raise ValueError(
                            f"Specialisation path {path.id} references unknown requirement {requirement_id}"
                        )
        return self

    def requirement_by_id(self, requirement_id: str) -> Requirement | None:
        return next((req for req in self.requirements if req.id == requirement_id), None)

    def pool_by_id(self, pool_id: str) -> CoursePool | None:
        return next((pool for pool in self.course_pools if pool.id == pool_id), None)

    def constraint_by_id(self, constraint_id: str) -> Constraint | None:
        return next((constraint for constraint in self.constraints if constraint.id == constraint_id), None)

    def alias_for(self, course_code: str) -> CourseAlias | None:
        normalized = course_code.upper().strip()
        return next((alias for alias in self.course_aliases if alias.alias.upper().strip() == normalized), None)
