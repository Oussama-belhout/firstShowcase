"""Refiner Agent — analyzes failures and generates improved Choco models."""

import re
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_llm, invoke_with_retry, MAX_REFINEMENT_ITERATIONS
from src.state import PipelineState, CSPSpecification, ChocoModel, SolverResult
from src.prompts.refiner import REFINER_SYSTEM, REFINER_HUMAN


def _extract_java_code(text: str) -> str:
    """Extract Java code from LLM response."""
    match = re.search(r'```java\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def _format_variables(spec: CSPSpecification) -> str:
    return "\n".join(f"  - {v.name}[{v.domain_low}..{v.domain_high}]: {v.description}" for v in spec.variables)


def _format_constraints(spec: CSPSpecification) -> str:
    return "\n".join(f"  - {c.formal_expression} ({c.description})" for c in spec.constraints)


def refiner_node(state: PipelineState) -> dict:
    """LangGraph node: Fix a failed Choco model based on error analysis."""
    llm = get_llm(temperature=0.2)  # Slightly higher temp for creative fixes

    spec = CSPSpecification(**state["csp_spec"])
    
    if "choco_model" not in state:
        return {
            "current_step": "refined",
            "status": "Skipped refinement (no model generated)",
            "iteration": state.get("iteration", 0)
        }
        
    model = ChocoModel(**state["choco_model"])
    iteration = state.get("iteration", 0) + 1

    validation = state.get("validation", {})
    solver_result_dict = state.get("solver_result", None)

    if not validation.get("is_valid", True) and "feedback" in validation:
        # Refinement triggered by validator
        error_status = "VALIDATION_ERROR"
        error_message = "\n".join(validation.get("feedback", ["Validation failed."]))
        stdout_text = ""
        stderr_text = ""
    elif solver_result_dict:
        # Refinement triggered by solver failure
        solver_res = SolverResult(**solver_result_dict)
        error_status = solver_res.status.value
        error_message = solver_res.error_message or "Solver execution failed."
        stdout_text = solver_res.stdout
        stderr_text = solver_res.stderr
    else:
        # Fallback
        error_status = "UNKNOWN_ERROR"
        error_message = "Refiner called without explicit errors in state."
        stdout_text = ""
        stderr_text = ""

    messages = [
        SystemMessage(content=REFINER_SYSTEM),
        HumanMessage(content=REFINER_HUMAN.format(
            status=error_status,
            error_message=error_message[:1500],
            stdout=stdout_text[:1500],
            stderr=stderr_text[:1500],
            problem_name=spec.problem_name,
            variables=_format_variables(spec),
            constraints=_format_constraints(spec),
            java_code=model.java_code,
            error_history="\n".join(state.get("error_history", [])),
            iteration=iteration,
            max_iterations=MAX_REFINEMENT_ITERATIONS,
            class_name=model.class_name,
        )),
    ]

    response = invoke_with_retry(llm, messages)
    fixed_code = _extract_java_code(response.content)

    # Ensure package declaration
    if "package runner;" not in fixed_code:
        fixed_code = "package runner;\n\n" + fixed_code

    refined_model = ChocoModel(
        java_code=fixed_code,
        class_name=model.class_name,
        explanation=f"Refined model (iteration {iteration}): {response.content[:200]}",
    )

    return {
        "choco_model": refined_model.model_dump(),
        "iteration": iteration,
        "current_step": "refined",
        "status": f"Model refined (attempt {iteration}/{MAX_REFINEMENT_ITERATIONS})",
    }
