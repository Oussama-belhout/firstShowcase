"""LangGraph workflow — orchestrates the multi-agent CSP solving pipeline."""

from langgraph.graph import StateGraph, END

from src.state import PipelineState, SolverStatus
from src.config import MAX_REFINEMENT_ITERATIONS
from src.agents.formalizer import formalizer_node
from src.agents.modeler import modeler_node
from src.agents.validator import validator_node
from src.agents.solver import solver_node
from src.agents.refiner import refiner_node
from src.agents.explainer import explainer_node


# ── Routing functions ─────────────────────────────────────────────────────────


def route_after_validation(state: PipelineState) -> str:
    """Route based on validation result: proceed to solver or go back to refiner."""
    validation = state.get("validation", {})
    if validation.get("is_valid", False):
        return "solver"
    else:
        # Check iteration limit
        iteration = state.get("iteration", 0)
        if iteration >= MAX_REFINEMENT_ITERATIONS:
            # Force solve anyway after max retries
            return "solver"
        return "refiner"


def route_after_solver(state: PipelineState) -> str:
    """Route based on solver result: explain success or refine failure."""
    solver_result = state.get("solver_result", {})
    status = solver_result.get("status", "")

    if status == SolverStatus.SUCCESS.value:
        return "explainer"
    else:
        # Check iteration limit
        iteration = state.get("iteration", 0)
        if iteration >= MAX_REFINEMENT_ITERATIONS:
            return "explainer"  # Explain the failure
        return "refiner"


# ── Build the graph ───────────────────────────────────────────────────────────


def build_workflow() -> StateGraph:
    """Build and compile the LangGraph workflow."""
    workflow = StateGraph(PipelineState)

    # Add all nodes
    workflow.add_node("formalizer", formalizer_node)
    workflow.add_node("modeler", modeler_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("solver", solver_node)
    workflow.add_node("refiner", refiner_node)
    workflow.add_node("explainer", explainer_node)

    # Set entry point
    workflow.set_entry_point("formalizer")

    # Define edges
    # formalizer → modeler (always)
    workflow.add_edge("formalizer", "modeler")

    # modeler → validator (always)
    workflow.add_edge("modeler", "validator")

    # validator → solver OR refiner (conditional)
    workflow.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "solver": "solver",
            "refiner": "refiner",
        }
    )

    # solver → explainer OR refiner (conditional)
    workflow.add_conditional_edges(
        "solver",
        route_after_solver,
        {
            "explainer": "explainer",
            "refiner": "refiner",
        }
    )

    # refiner → modeler (loop back, but skip the formalizer — spec is fine)
    workflow.add_edge("refiner", "modeler")

    # explainer → END
    workflow.add_edge("explainer", END)

    return workflow.compile()


def run_pipeline(problem_description: str) -> dict:
    """Run the full CSP solving pipeline."""
    graph = build_workflow()

    initial_state = {
        "problem_description": problem_description,
        "iteration": 0,
        "error_history": [],
        "current_step": "starting",
        "status": "Pipeline started",
        "messages": [],
    }

    # Run with streaming for progress updates
    final_state = graph.invoke(initial_state)
    return final_state


def stream_pipeline(problem_description: str):
    """Stream the pipeline execution for real-time UI updates."""
    graph = build_workflow()

    initial_state = {
        "problem_description": problem_description,
        "iteration": 0,
        "error_history": [],
        "current_step": "starting",
        "status": "Pipeline started",
        "messages": [],
    }

    # Yield intermediate states
    for event in graph.stream(initial_state, stream_mode="updates"):
        yield event
