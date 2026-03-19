"""Validator Agent — validates generated Choco models against CSP specifications."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_llm, invoke_structured_with_retry
from src.state import PipelineState, CSPSpecification, ChocoModel, ValidationResult
from src.prompts.validator import VALIDATOR_SYSTEM, VALIDATOR_HUMAN


def _format_variables_short(spec: CSPSpecification) -> str:
    return ", ".join(f"{v.name}[{v.domain_low}..{v.domain_high}]" for v in spec.variables)


def _format_constraints_short(spec: CSPSpecification) -> str:
    return "\n".join(f"  - {c.formal_expression} ({c.description})" for c in spec.constraints)


def validator_node(state: PipelineState) -> dict:
    """LangGraph node: Validate the generated Choco model against the specification."""
    llm = get_llm()
    structured_llm = llm.with_structured_output(ValidationResult)

    spec = CSPSpecification(**state["csp_spec"])
    
    if "choco_model" not in state:
        return {
            "validation": {"is_valid": False, "issues": ["Model was skipped; nothing to validate."], "suggestions": []},
            "current_step": "validated",
            "status": "validation_skipped_no_model",
        }
        
    model = ChocoModel(**state["choco_model"])

    messages = [
        SystemMessage(content=VALIDATOR_SYSTEM),
        HumanMessage(content=VALIDATOR_HUMAN.format(
            problem_name=spec.problem_name,
            variables=_format_variables_short(spec),
            constraints=_format_constraints_short(spec),
            objective=spec.objective or "None",
            java_code=model.java_code,
        )),
    ]

    result: ValidationResult = invoke_structured_with_retry(structured_llm, messages)

    return {
        "validation": result.model_dump(),
        "current_step": "validated",
        "status": "valid" if result.is_valid else "validation_failed",
    }
