"""Solver Agent — compiles and runs Choco models, collects results and monitor traces."""

from src.state import PipelineState, ChocoModel, SolverResult, SolverStatus
from src.choco.bridge import compile_and_run_model
from src.choco.parser import parse_solver_output


def solver_node(state: PipelineState) -> dict:
    """LangGraph node: Compile and run the Choco model, collect results."""
    if "choco_model" not in state:
        solver_result = SolverResult(
            status=SolverStatus.RUNTIME_ERROR,
            error_message="Cannot run solver: Model was skipped or not generated.",
            stdout="",
            stderr=""
        )
        return {
            "solver_result": solver_result.model_dump(),
            "current_step": "solved",
            "status": solver_result.status.value,
        }
    
    model = ChocoModel(**state["choco_model"])

    # Run via the Choco bridge
    bridge_result = compile_and_run_model(
        java_code=model.java_code,
        class_name=model.class_name,
    )

    # Parse the output
    if bridge_result["status"] == "compilation_error":
        solver_result = SolverResult(
            status=SolverStatus.COMPILATION_ERROR,
            error_message=bridge_result["stderr"],
            stdout=bridge_result.get("stdout", ""),
            stderr=bridge_result["stderr"],
        )
    elif bridge_result["status"] == "runtime_error":
        solver_result = SolverResult(
            status=SolverStatus.RUNTIME_ERROR,
            error_message=bridge_result["stderr"],
            stdout=bridge_result.get("stdout", ""),
            stderr=bridge_result["stderr"],
        )
    elif bridge_result["status"] == "timeout":
        solver_result = SolverResult(
            status=SolverStatus.TIMEOUT,
            error_message="Solver exceeded time limit",
            stdout=bridge_result.get("stdout", ""),
            stderr=bridge_result.get("stderr", ""),
        )
    else:
        # Parse successful output
        parsed = parse_solver_output(bridge_result["stdout"])
        solver_result = SolverResult(
            status=SolverStatus.SUCCESS if parsed["has_solution"] else SolverStatus.NO_SOLUTION,
            solution=parsed["solution"],
            solution_text=parsed["solution_text"],
            statistics=parsed["statistics"],
            monitor_traces=parsed["monitor_traces"],
            stdout=bridge_result["stdout"],
            stderr=bridge_result.get("stderr", ""),
        )

    # Track errors for refinement
    error_history = state.get("error_history", [])
    if solver_result.status != SolverStatus.SUCCESS:
        error_history = error_history + [
            f"Iteration {state.get('iteration', 0)}: {solver_result.status.value} — {solver_result.error_message[:300]}"
        ]

    return {
        "solver_result": solver_result.model_dump(),
        "error_history": error_history,
        "current_step": "solved",
        "status": solver_result.status.value,
    }
