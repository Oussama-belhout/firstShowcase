"""Explainer Agent — generates human-readable explanations of the solving process."""

from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_llm, invoke_with_retry
from src.state import PipelineState, CSPSpecification, SolverResult
from src.prompts.explainer import EXPLAINER_SYSTEM, EXPLAINER_HUMAN


def _format_variables(spec: CSPSpecification) -> str:
    return "\n".join(f"  - {v.name}[{v.domain_low}..{v.domain_high}]: {v.description}" for v in spec.variables)


def _format_constraints(spec: CSPSpecification) -> str:
    return "\n".join(f"  - {c.formal_expression} ({c.description})" for c in spec.constraints)


def explainer_node(state: PipelineState) -> dict:
    """LangGraph node: Explain the solving process using monitor traces and statistics."""
    llm = get_llm(temperature=0.3)  # Slightly creative for pedagogical explanations

    spec = CSPSpecification(**state["csp_spec"])
    
    if "solver_result" not in state:
        return {
            "explanation": "No solver result provided. The solver was likely skipped.",
            "current_step": "explained",
            "status": "Skipped explanation",
        }
        
    solver_result = SolverResult(**state["solver_result"])

    messages = [
        SystemMessage(content=EXPLAINER_SYSTEM),
        HumanMessage(content=EXPLAINER_HUMAN.format(
            problem_name=spec.problem_name,
            problem_description=spec.problem_description,
            variables=_format_variables(spec),
            constraints=_format_constraints(spec),
            solution_text=solver_result.solution_text or str(solver_result.solution),
            statistics=str(solver_result.statistics),
            monitor_traces="\n".join(solver_result.monitor_traces) if solver_result.monitor_traces else "No monitor traces available",
        )),
    ]

    response = invoke_with_retry(llm, messages)

    return {
        "explanation": response.content,
        "current_step": "explained",
        "status": "Complete — solution explained",
    }
