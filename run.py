"""
Quick CLI runner — runs the CSP pipeline and shows results in LangSmith.
Usage: python run.py "Place 4 queens on a 4x4 chessboard..."
"""

import sys
import os
import json
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

try:
    from langchain_core.tracers.langchain import wait_for_all_tracers
except Exception:
    def wait_for_all_tracers() -> None:
        return None


def _is_true(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _flush_traces() -> None:
    """Best-effort flush of LangSmith/LangChain background callbacks."""
    try:
        # Small delay helps in-flight callbacks reach the transport.
        time.sleep(0.3)
        wait_for_all_tracers()
        time.sleep(0.3)
    except Exception:
        pass


def _configure_tracing_env() -> None:
    """Normalize old/new LangSmith env var names and enable tracing when possible."""
    langsmith_key = os.getenv("LANGSMITH_API_KEY")
    langchain_key = os.getenv("LANGCHAIN_API_KEY")

    # Mirror keys for compatibility across package versions.
    if langsmith_key and not langchain_key:
        os.environ["LANGCHAIN_API_KEY"] = langsmith_key
    if langchain_key and not langsmith_key:
        os.environ["LANGSMITH_API_KEY"] = langchain_key

    project = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")
    if project:
        os.environ.setdefault("LANGSMITH_PROJECT", project)
        os.environ.setdefault("LANGCHAIN_PROJECT", project)

    tracing_enabled = _is_true(os.getenv("LANGSMITH_TRACING")) or _is_true(os.getenv("LANGCHAIN_TRACING_V2"))
    has_key = bool(os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"))

    # If we have a key, force tracing on for both naming conventions.
    if has_key and not tracing_enabled:
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
    elif tracing_enabled:
        os.environ.setdefault("LANGSMITH_TRACING", "true")
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")


_configure_tracing_env()

# Make trace delivery synchronous for CLI robustness so Ctrl+C keeps partial traces.
os.environ.setdefault("LANGCHAIN_CALLBACKS_BACKGROUND", "false")
os.environ.setdefault("LANGSMITH_CALLBACKS_BACKGROUND", "false")

print("=" * 60)
print("CSP Solver - Multi-Agent Pipeline")
print("=" * 60)
print(f"  LangSmith tracing: {os.getenv('LANGSMITH_TRACING', os.getenv('LANGCHAIN_TRACING_V2', 'NOT SET'))}")
print(f"  LangSmith project: {os.getenv('LANGSMITH_PROJECT', os.getenv('LANGCHAIN_PROJECT', 'NOT SET'))}")
print(f"  Model: {os.getenv('MODEL_NAME', 'gpt-4o')}")
print(f"  API Key set: {'Yes' if os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"  LangSmith Key set: {'Yes' if os.getenv('LANGSMITH_API_KEY') or os.getenv('LANGCHAIN_API_KEY') else 'No'}")
print("=" * 60)

if not (os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")):
    print("WARNING: LangSmith API key is missing. No traces can be uploaded.")
    print("Set LANGSMITH_API_KEY (or LANGCHAIN_API_KEY) before running experiments.")
    print("=" * 60)

from src.graph.workflow import build_workflow

# Default problem or from CLI args
DEFAULT_PROBLEM = "Place 4 queens on a 4×4 chessboard such that no two queens threaten each other. No two queens can share the same row, column, or diagonal."

# Intercept arguments
args = sys.argv[1:]

is_local = False
if "-local" in args:
    is_local = True
    args.remove("-local")
elif "--local" in args:
    is_local = True
    args.remove("--local")

# Check for agents to skip (e.g., -modeler, -validator)
skip_agents = []
temp_args = []
for arg in args:
    if arg.startswith("-"):
        # e.g., -modeler -> modeler
        agent_name = arg.lstrip("-")
        skip_agents.append(agent_name)
    else:
        temp_args.append(arg)
args = temp_args

if is_local:
    os.environ["LLM_PROVIDER"] = "ollama"
    print("Local Mode Activated: Using Ollama (LangSmith tracing remains enabled if configured).")

if skip_agents:
    print(f"Skipping Agents: {', '.join(skip_agents)}")
    
print("\n")

problem = " ".join(args) if args else DEFAULT_PROBLEM

print(f"\nProblem: {problem}\n")
print("-" * 60)

# Build and run the graph
graph = build_workflow()

initial_state = {
    "problem_description": problem,
    "iteration": 0,
    "error_history": [],
    "current_step": "starting",
    "status": "Pipeline started",
    "messages": [],
    "skip_agents": skip_agents,
}

# Stream with updates to see each agent step
if is_local:
    print("\nRunning pipeline (Locally with Ollama, tracing -> LangSmith)...\n")
else:
    print("\nRunning pipeline (all traces -> LangSmith)...\n")

try:
    for event in graph.stream(initial_state, stream_mode=["updates", "messages"]):
        # event is a tuple of (stream_mode, data) when multiple stream_modes are used
        mode, chunk = event

        if mode == "messages":
            # Stream the LLM tokens directly to the console.
            message, metadata = chunk
            if message.__class__.__name__ == "AIMessageChunk":
                print(message.content, end="", flush=True)

        elif mode == "updates":
            # Print a newline if we just finished streaming tokens.
            print()
            for node_name, node_output in chunk.items():
                step = node_output.get("current_step", node_name)
                status = node_output.get("status", "")
                print(f"\n  [{node_name}] -> {status}")

                # Show key info for each step
                if node_name == "formalizer":
                    spec = node_output.get("csp_spec", {})
                    print(f"     Variables: {len(spec.get('variables', []))}")
                    print(f"     Constraints: {len(spec.get('constraints', []))}")

                elif node_name == "modeler":
                    model = node_output.get("choco_model", {})
                    code = model.get("java_code", "")
                    print(f"     Generated: {model.get('class_name', '?')}.java ({len(code)} chars)")

                elif node_name == "validator":
                    val = node_output.get("validation", {})
                    print(f"     Valid: {val.get('is_valid', '?')}")
                    for issue in val.get("issues", []):
                        print(f"     !  {issue}")

                elif node_name == "solver":
                    result = node_output.get("solver_result", {})
                    print(f"     Status: {result.get('status', '?')}")
                    if result.get("solution"):
                        print(f"     Solution: {result['solution']}")
                    if result.get("error_message"):
                        print(f"     Error: {result['error_message'][:200]}")
                    stats = result.get("statistics", {})
                    if stats:
                        print(f"     Stats: {json.dumps(stats, indent=2)}")

                elif node_name == "refiner":
                    print(f"     Iteration: {node_output.get('iteration', '?')}")

                elif node_name == "explainer":
                    explanation = node_output.get("explanation", "")
                    print(f"     Explanation: {explanation[:300]}...")

                print("-" * 60)
except KeyboardInterrupt:
    print("\n\nInterrupted by user (Ctrl+C). Flushing traces to LangSmith...")
    _flush_traces()
    print("Partial traces should now be visible in LangSmith.")
    sys.exit(130)
except Exception:
    _flush_traces()
    raise
finally:
    _flush_traces()
print("-" * 60)
print("Pipeline complete! Check LangSmith for full traces:")
print("   https://smith.langchain.com")
print("-" * 60)
