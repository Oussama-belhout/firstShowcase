"""Modeler Agent — generates Choco Solver Java code from CSP specifications."""

import re
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_llm, invoke_with_retry
from src.state import PipelineState, CSPSpecification, ChocoModel
from src.prompts.modeler import MODELER_SYSTEM, MODELER_HUMAN


def _format_variables(spec: CSPSpecification) -> str:
    """Format variables for the prompt."""
    lines = []
    for v in spec.variables:
        lines.append(f"  - {v.name}: [{v.domain_low}..{v.domain_high}] — {v.description}")
    return "\n".join(lines)


def _format_constraints(spec: CSPSpecification) -> str:
    """Format constraints for the prompt."""
    lines = []
    for i, c in enumerate(spec.constraints, 1):
        lines.append(f"  {i}. [{c.constraint_type}] {c.description}")
        lines.append(f"     Formal: {c.formal_expression}")
    return "\n".join(lines)


def _generate_class_name(problem_name: str) -> str:
    """Generate a valid Java class name from problem name."""
    # Remove non-alphanumeric, capitalize words
    words = re.sub(r'[^a-zA-Z0-9\s]', '', problem_name).split()
    return "".join(w.capitalize() for w in words) + "Solver"


def _extract_java_code(text: str) -> str:
    """Extract Java code from LLM response (may be wrapped in markdown code blocks)."""
    # Try to extract from code block
    match = re.search(r'```java\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Try generic code block
    match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    # Return as-is if no code blocks
    return text.strip()


def modeler_node(state: PipelineState) -> dict:
    """LangGraph node: Generate Choco Solver Java code from CSP specification."""
    llm = get_llm()
    spec = CSPSpecification(**state["csp_spec"])
    class_name = _generate_class_name(spec.problem_name)

    messages = [
        SystemMessage(content=MODELER_SYSTEM),
        HumanMessage(content=MODELER_HUMAN.format(
            problem_name=spec.problem_name,
            problem_description=spec.problem_description,
            parameters=spec.parameters,
            variables=_format_variables(spec),
            constraints=_format_constraints(spec),
            objective=spec.objective or "None (satisfaction problem)",
            class_name=class_name,
        )),
    ]

    response = invoke_with_retry(llm, messages)
    java_code = _extract_java_code(response.content)

    # Ensure package declaration
    if "package runner;" not in java_code:
        java_code = "package runner;\n\n" + java_code

    model = ChocoModel(
        java_code=java_code,
        class_name=class_name,
        explanation=f"Generated Choco model for {spec.problem_name}",
    )

    return {
        "choco_model": model.model_dump(),
        "current_step": "modeled",
        "status": "Choco model generated",
    }
