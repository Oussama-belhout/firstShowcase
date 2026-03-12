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

SEQUENCE = ["formalizer", "modeler", "validator", "solver", "explainer"]

def dynamic_router(state: PipelineState, current_node: str) -> str:
    """Finds the next node in the sequence that is not being skipped."""
    skip_agents = state.get("skip_agents", [])
    
    try:
        current_idx = SEQUENCE.index(current_node)
    except ValueError:
        return END

    # Look ahead for the next unskipped node
    for i in range(current_idx + 1, len(SEQUENCE)):
        next_node = SEQUENCE[i]
        if next_node not in skip_agents:
            return next_node

    return END

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

    # Calculate Entry Point
    # The entry point should be the first agent in the sequence that isn't skipped
    # (Since we can't reliably read the state at init time for the entry point, 
    # we usually just route to an internal start node, but LangGraph allows 
    # conditional entry points in recent versions!)
    
    # For now, we'll route from a dummy __start__ if possible, or just require 
    # that 'formalizer' is never the ONE node skipped if it's the hardcoded entry.
    # Actually wait - we can just define a conditional entry point:
    workflow.add_conditional_edges(
        "__start__",
        lambda state: dynamic_router(state, "") if dynamic_router(state, "") != END else "formalizer" # fallback
    )

    # Define edges using our dynamic router

    # formalizer → next
    workflow.add_conditional_edges("formalizer", lambda state: dynamic_router(state, "formalizer"))

    # modeler → next
    workflow.add_conditional_edges("modeler", lambda state: dynamic_router(state, "modeler"))

    # validator → solver OR refiner (conditional loop) OR next
    def handle_validator(state: PipelineState) -> str:
        validation = state.get("validation", {})
        if validation.get("is_valid", False):
            return dynamic_router(state, "validator")
        else:
            iteration = state.get("iteration", 0)
            if iteration >= MAX_REFINEMENT_ITERATIONS:
                return dynamic_router(state, "validator")
            # Loop
            if "refiner" in state.get("skip_agents", []):
                return dynamic_router(state, "validator")
            return "refiner"
            
    workflow.add_conditional_edges("validator", handle_validator)

    # solver → explainer OR refiner (conditional loop) OR next
    def handle_solver(state: PipelineState) -> str:
        solver_result = state.get("solver_result", {})
        status = solver_result.get("status", "")

        if status == SolverStatus.SUCCESS.value:
            return dynamic_router(state, "solver")
        else:
            iteration = state.get("iteration", 0)
            if iteration >= MAX_REFINEMENT_ITERATIONS:
                return dynamic_router(state, "solver")
            if "refiner" in state.get("skip_agents", []):
                return dynamic_router(state, "solver")
            return "refiner"
            
    workflow.add_conditional_edges("solver", handle_solver)

    # refiner → modeler (loop back)
    # If modeler is skipped, go to validator, etc.
    def handle_refiner(state: PipelineState) -> str:
        # It loops back before the modeling step
        # To find the next agent we pretend we are back before the modeler
        return dynamic_router(state, "formalizer")
        
    workflow.add_conditional_edges("refiner", handle_refiner)

    # explainer → END
    workflow.add_conditional_edges("explainer", lambda state: dynamic_router(state, "explainer"))

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
        "skip_agents": [],
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
        "skip_agents": [],
    }

    # Yield intermediate states
    for event in graph.stream(initial_state, stream_mode="updates"):
        yield event
