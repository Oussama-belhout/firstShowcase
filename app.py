"""
CSP Solver Multi-Agent System — Streamlit Web UI
Automatic resolution of combinatorial problems using LLMs and Choco constraint programming.
"""

import streamlit as st
import json
import time
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from src.graph.workflow import build_workflow

# ── Page Config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="CSP Solver - Multi-Agent System",
    page_icon="cube",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    .stApp {
        font-family: 'Inter', sans-serif;
    }

    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem 2.5rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
    }

    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
    }

    .main-header p {
        margin: 0.5rem 0 0 0;
        opacity: 0.9;
        font-size: 1rem;
        font-weight: 300;
    }

    .agent-card {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.2rem 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }

    .agent-card:hover {
        border-color: rgba(102, 126, 234, 0.4);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.15);
    }

    .agent-card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1rem;
        font-weight: 600;
    }

    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.8rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .status-running { background: rgba(251, 191, 36, 0.2); color: #fbbf24; }
    .status-success { background: rgba(34, 197, 94, 0.2); color: #22c55e; }
    .status-error   { background: rgba(239, 68, 68, 0.2); color: #ef4444; }
    .status-pending { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }

    .pipeline-flow {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        padding: 1rem;
        flex-wrap: wrap;
    }

    .pipeline-node {
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        font-weight: 500;
        text-align: center;
        min-width: 100px;
    }

    .pipeline-arrow {
        font-size: 1.2rem;
        color: #64748b;
    }

    .node-active  { background: #667eea; color: white; }
    .node-done    { background: #22c55e; color: white; }
    .node-error   { background: #ef4444; color: white; }
    .node-pending { background: #334155; color: #94a3b8; }

    .metric-card {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
    }

    .metric-value {
        font-size: 2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .metric-label {
        font-size: 0.85rem;
        color: #94a3b8;
        margin-top: 0.3rem;
    }

    .stTextArea > div > div > textarea {
        border-radius: 12px !important;
        border: 2px solid rgba(102, 126, 234, 0.3) !important;
        font-family: 'Inter', sans-serif !important;
    }

    .stTextArea > div > div > textarea:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.15) !important;
    }

    div.stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 12px;
        padding: 0.7rem 2rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        width: 100%;
    }

    div.stButton > button:hover {
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.4);
        transform: translateY(-1px);
    }

    .preset-btn button {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        font-size: 0.85rem !important;
    }

    .langsmith-link {
        background: linear-gradient(145deg, #1e1e2e, #2a2a3e);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 12px;
        padding: 1rem 1.5rem;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Preset Problems ───────────────────────────────────────────────────────────

PRESETS = {
    "4-Queens": "Place 4 queens on a 4×4 chessboard such that no two queens threaten each other. No two queens can share the same row, column, or diagonal.",
    "8-Queens": "Place 8 queens on an 8×8 chessboard such that no two queens threaten each other. No two queens can share the same row, column, or diagonal.",
    "Sudoku (Easy)": """Solve a 4x4 Sudoku puzzle. Place digits 1-4 in a 4×4 grid so that each row, each column, and each 2×2 box contains all digits from 1 to 4.
Given clues: Row 1: [_, 2, _, 4], Row 2: [4, _, 2, _], Row 3: [_, 4, _, 2], Row 4: [2, _, 4, _]
Where _ means the cell needs to be filled.""",
    "Magic Square 3×3": "Create a 3×3 magic square where all rows, all columns, and both diagonals sum to the same value (15). Use each integer from 1 to 9 exactly once.",
    "Graph Coloring": "Color the vertices of a graph with 4 vertices and edges (1-2, 2-3, 3-4, 4-1, 1-3) using at most 3 colors such that no two adjacent vertices share the same color.",
    "Send More Money": "Solve the cryptarithmetic puzzle: SEND + MORE = MONEY. Each letter represents a unique digit (0-9). S and M cannot be 0.",
}

# ── Pipeline Step Definitions ─────────────────────────────────────────────────

PIPELINE_STEPS = [
    ("formalizer", "Formalizer", "Analyzing problem"),
    ("modeler", "Modeler", "Generating Choco code"),
    ("validator", "Validator", "Validating model"),
    ("solver", "Solver", "Running Choco solver"),
    ("refiner", "Refiner", "Refining model"),
    ("explainer", "Explainer", "Explaining solution"),
]

# ── Helper Functions ──────────────────────────────────────────────────────────


def get_step_status(step_key: str, completed_steps: list, current_step: str, error_step: str = None):
    """Get visual status for a pipeline step."""
    if error_step == step_key:
        return "error", "ERROR"
    if step_key in completed_steps:
        return "done", "DONE"
    if step_key == current_step:
        return "active", "ACTIVE"
    return "pending", "PENDING"


def render_pipeline_flow(completed_steps: list, current_step: str):
    """Render the pipeline flow visualization."""
    cols = st.columns(len(PIPELINE_STEPS))
    for i, (key, label, _) in enumerate(PIPELINE_STEPS):
        status, icon = get_step_status(key, completed_steps, current_step)
        with cols[i]:
            if status == "done":
                st.success(f"{label}", icon="check")
            elif status == "active":
                st.warning(f"{label}", icon="sync")
            elif status == "error":
                st.error(f"{label}", icon="stop")
            else:
                st.info(f"{label}", icon="circle")


# ── Main App ──────────────────────────────────────────────────────────────────

# Main content
# Header
st.markdown("""
<div class="main-header">
    <h1>CSP Solver - Multi-Agent System</h1>
    <p>Automatic resolution of combinatorial problems using LLMs & Choco constraint programming</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.markdown("### Quick Start")
    st.markdown("Select a preset problem or enter your own:")

    st.markdown("---")
    st.markdown("### Preset Problems")

    selected_preset = None
    for name, desc in PRESETS.items():
        if st.button(f"> {name}", key=f"preset_{name}", use_container_width=True):
            selected_preset = desc
            st.session_state["problem_input"] = desc

    st.markdown("---")
    st.markdown("### Configuration")
    model_name = os.getenv("MODEL_NAME", "gpt-4o")
    st.markdown(f"**Model:** `{model_name}`")
    st.markdown(f"**Max Retries:** `{os.getenv('MAX_REFINEMENT_ITERATIONS', '3')}`")
    st.markdown(f"**Timeout:** `{os.getenv('SOLVER_TIMEOUT_SECONDS', '30')}s`")

    st.markdown("---")
    st.markdown("""
    <div class="langsmith-link">
        <strong>LangSmith Dashboard</strong><br>
        <a href="https://smith.langchain.com" target="_blank" style="color: #667eea;">
            View traces & monitoring ->
        </a>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <p style="font-size: 0.75rem; color: #64748b; text-align: center;">
        Built with LangGraph • LangSmith • Choco Solver
    </p>
    """, unsafe_allow_html=True)

# Main content
col_input, col_status = st.columns([2, 1])

with col_input:
    problem = st.text_area(
        "Describe your combinatorial problem",
        value=st.session_state.get("problem_input", ""),
        height=150,
        placeholder="e.g., Place 4 queens on a 4x4 chessboard such that no two queens threaten each other...",
    )

with col_status:
    st.markdown("### Pipeline Status")
    if "pipeline_running" in st.session_state and st.session_state["pipeline_running"]:
        st.markdown(f'<span class="status-badge status-running">Running</span>', unsafe_allow_html=True)
    elif "pipeline_result" in st.session_state:
        result = st.session_state["pipeline_result"]
        if result.get("solver_result", {}).get("status") == "success":
            st.markdown(f'<span class="status-badge status-success">Solved</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="status-badge status-error">Failed</span>', unsafe_allow_html=True)
    else:
        st.markdown(f'<span class="status-badge status-pending">Ready</span>', unsafe_allow_html=True)

# Run button
if st.button("Solve Problem", use_container_width=True, disabled=not problem):
    if not problem.strip():
        st.error("Please enter a problem description.")
    else:
        st.session_state["pipeline_running"] = True
        st.session_state["pipeline_result"] = None
        st.session_state["step_results"] = {}

        # Build the workflow
        graph = build_workflow()

        initial_state = {
            "problem_description": problem.strip(),
            "iteration": 0,
            "error_history": [],
            "current_step": "starting",
            "status": "Pipeline started",
            "messages": [],
        }

        # Progress section
        st.markdown("---")
        st.markdown("## Pipeline Execution")

        progress_bar = st.progress(0)
        status_text = st.empty()
        completed_steps = []

        # Pipeline flow visualization
        flow_container = st.empty()

        # Step output containers
        step_containers = {}

        try:
            step_count = 0
            total_steps = 6  # Max steps (might be fewer if no refinement)

            for event in graph.stream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    step_count += 1
                    completed_steps.append(node_name)

                    # Update progress
                    progress = min(step_count / total_steps, 1.0)
                    progress_bar.progress(progress)

                    # Find the step label
                    step_label = node_name
                    for key, label, _ in PIPELINE_STEPS:
                        if key == node_name:
                            step_label = label
                            break

                    status_text.markdown(f"**Current:** {step_label}")

                    # Update flow visualization
                    with flow_container.container():
                        render_pipeline_flow(completed_steps, node_name)

                    # Store results
                    st.session_state["step_results"][node_name] = node_output

                    # Get the cumulative state by merging
                    if "pipeline_result" not in st.session_state or st.session_state["pipeline_result"] is None:
                        st.session_state["pipeline_result"] = {}
                    st.session_state["pipeline_result"].update(node_output)

            progress_bar.progress(1.0)
            status_text.markdown("**Pipeline complete!**")
            st.session_state["pipeline_running"] = False

        except Exception as e:
            st.error(f"Pipeline error: {str(e)}")
            st.session_state["pipeline_running"] = False
            import traceback
            st.code(traceback.format_exc())

        # ── Results Display ───────────────────────────────────────────────

        final_result = st.session_state.get("pipeline_result", {})

        if final_result:
            st.markdown("---")
            st.markdown("## Results")

            # Metrics row
            solver_result = final_result.get("solver_result", {})
            stats = solver_result.get("statistics", {})

            m1, m2, m3, m4 = st.columns(4)
            with m1:
                status_emoji = "SUCCESS" if solver_result.get("status") == "success" else "FAILED"
                st.metric("Status", f"{status_emoji}")
            with m2:
                st.metric("Iterations", final_result.get("iteration", 0))
            with m3:
                st.metric("Nodes Explored", stats.get("nodes", "N/A"))
            with m4:
                st.metric("Backtracks", stats.get("backtracks", "N/A"))

            # Detailed results in tabs
            tab_spec, tab_code, tab_solution, tab_explain, tab_traces, tab_raw = st.tabs([
                "CSP Spec", "Generated Code", "Solution",
                "Explanation", "Monitor Traces", "Raw Data"
            ])

            with tab_spec:
                spec = final_result.get("csp_spec", {})
                if spec:
                    st.markdown(f"### {spec.get('problem_name', 'Problem')}")
                    st.markdown(spec.get("problem_description", ""))

                    st.markdown("#### Variables")
                    for v in spec.get("variables", []):
                        st.markdown(f"- **{v['name']}** ∈ [{v['domain_low']}..{v['domain_high']}] — {v.get('description', '')}")

                    st.markdown("#### Constraints")
                    for c in spec.get("constraints", []):
                        st.markdown(f"- `{c['formal_expression']}` — {c['description']}")

                    if spec.get("parameters"):
                        st.markdown("#### Parameters")
                        st.json(spec["parameters"])

            with tab_code:
                model = final_result.get("choco_model", {})
                if model:
                    st.markdown(f"**Class:** `{model.get('class_name', 'N/A')}`")
                    st.code(model.get("java_code", "No code generated"), language="java")

            with tab_solution:
                if solver_result.get("status") == "success":
                    st.success("Solution found!")
                    solution = solver_result.get("solution", {})
                    if solution:
                        # Nice display
                        cols = st.columns(min(len(solution), 4))
                        for i, (var, val) in enumerate(solution.items()):
                            with cols[i % len(cols)]:
                                st.metric(var, val)
                    st.markdown("**Raw solution:**")
                    st.code(solver_result.get("solution_text", ""), language="text")
                elif solver_result.get("status") == "no_solution":
                    st.warning("No solution found.")
                else:
                    st.error(f"Solver failed: {solver_result.get('error_message', 'Unknown error')}")

                if solver_result.get("stderr"):
                    with st.expander("Stderr Output"):
                        st.code(solver_result["stderr"], language="text")

            with tab_explain:
                explanation = final_result.get("explanation", "")
                if explanation:
                    st.markdown(explanation)
                else:
                    st.info("No explanation generated yet.")

            with tab_traces:
                st.markdown("### Solver Statistics")
                if stats:
                    st.json(stats)

                st.markdown("### Monitor Traces")
                traces = solver_result.get("monitor_traces", [])
                if traces:
                    for trace in traces:
                        st.code(trace, language="text")
                else:
                    st.info("No monitor traces captured. Check [LangSmith](https://smith.langchain.com) for full agent execution traces.")

                st.markdown("### LangSmith Traces")
                st.markdown("""
                All agent interactions are traced in LangSmith.
                [Open LangSmith Dashboard →](https://smith.langchain.com)
                """)

                # Error history
                errors = final_result.get("error_history", [])
                if errors:
                    st.markdown("### Refinement History")
                    for err in errors:
                        st.warning(err)

            with tab_raw:
                st.json(final_result)

# Footer with info
if "pipeline_result" not in st.session_state:
    st.markdown("---")

    st.markdown("### Architecture")
    st.markdown("""
    This system uses a **LangGraph multi-agent pipeline** with 6 specialized agents:

    | Agent | Role |
    |-------|------|
    | **Formalizer** | Parses natural language -> structured CSP specification |
    | **Modeler**    | Generates Choco Solver Java code from the specification |
    | **Validator**  | Validates the generated model against the specification |
    | **Solver**     | Compiles & executes the Choco model |
    | **Refiner**    | Fixes errors through iterative improvement (up to 3 retries) |
    | **Explainer**  | Produces pedagogical explanations of the solving process |

    All agent calls are traced via **LangSmith** for full observability.
    """)
