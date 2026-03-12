"""Shared state models for the LangGraph pipeline."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Any

from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


# ── Structured CSP Specification ──────────────────────────────────────────────


class VariableSpec(BaseModel):
    """A CSP variable definition."""
    name: str = Field(description="Variable name")
    domain_low: int = Field(description="Lower bound of the integer domain")
    domain_high: int = Field(description="Upper bound of the integer domain")
    description: str = Field(default="", description="What this variable represents")


class ConstraintSpec(BaseModel):
    """A single constraint definition."""
    description: str = Field(description="Natural language description of the constraint")
    formal_expression: str = Field(description="Formal/mathematical expression of the constraint")
    constraint_type: str = Field(
        default="custom",
        description="Type: allDifferent, arithm, table, element, count, global, custom"
    )


class CSPSpecification(BaseModel):
    """Structured specification of a Constraint Satisfaction Problem."""
    problem_name: str = Field(description="Short identifier for the problem")
    problem_description: str = Field(description="Full natural language description")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Problem parameters (e.g., N=8)")
    variables: list[VariableSpec] = Field(description="All decision variables")
    constraints: list[ConstraintSpec] = Field(description="All constraints")
    objective: str | None = Field(default=None, description="Optimization objective if applicable")
    is_optimization: bool = Field(default=False, description="Whether this is an optimization problem")


# ── Choco Model ───────────────────────────────────────────────────────────────


class ChocoModel(BaseModel):
    """Generated Choco solver Java code."""
    java_code: str = Field(description="Complete Java source code for the Choco model")
    class_name: str = Field(description="Java class name")
    explanation: str = Field(default="", description="LLM's explanation of the generated model")


# ── Solver Result ─────────────────────────────────────────────────────────────


class SolverStatus(str, Enum):
    SUCCESS = "success"
    NO_SOLUTION = "no_solution"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR = "runtime_error"
    TIMEOUT = "timeout"


class SolverResult(BaseModel):
    """Result from running the Choco solver."""
    status: SolverStatus = Field(description="Outcome status")
    solution: dict[str, Any] = Field(default_factory=dict, description="Variable assignments if solved")
    solution_text: str = Field(default="", description="Raw solution output text")
    statistics: dict[str, Any] = Field(default_factory=dict, description="Solver statistics")
    monitor_traces: list[str] = Field(default_factory=list, description="Monitor output lines")
    error_message: str = Field(default="", description="Error details if failed")
    stdout: str = Field(default="", description="Full stdout from solver")
    stderr: str = Field(default="", description="Full stderr from solver")


# ── Validation Result ─────────────────────────────────────────────────────────


class ValidationResult(BaseModel):
    """Result of model validation."""
    is_valid: bool = Field(description="Whether the model passes validation")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    suggestions: list[str] = Field(default_factory=list, description="Suggestions for improvement")


# ── Pipeline State (LangGraph TypedDict-style) ────────────────────────────────


from typing import TypedDict


class PipelineState(TypedDict, total=False):
    """Full LangGraph pipeline state."""
    # Input
    problem_description: str
    
    # Formalizer output
    csp_spec: dict  # Serialized CSPSpecification
    
    # Modeler output
    choco_model: dict  # Serialized ChocoModel
    
    # Validator output
    validation: dict  # Serialized ValidationResult
    
    # Solver output
    solver_result: dict  # Serialized SolverResult
    
    # Explainer output
    explanation: str
    
    # Refiner state
    error_history: list[str]
    iteration: int
    
    # Pipeline metadata
    current_step: str
    status: str
    messages: Annotated[list, add_messages]
