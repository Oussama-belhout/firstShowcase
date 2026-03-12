"""
Quick CLI runner — runs the CSP pipeline and shows results in LangSmith.
Usage: python run.py "Place 4 queens on a 4x4 chessboard..."
"""

import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Verify LangSmith is configured
print("=" * 60)
print("🔧 CSP Solver — Multi-Agent Pipeline")
print("=" * 60)
print(f"  LangSmith tracing: {os.getenv('LANGCHAIN_TRACING_V2', 'NOT SET')}")
print(f"  LangSmith project: {os.getenv('LANGCHAIN_PROJECT', 'NOT SET')}")
print(f"  Model: {os.getenv('MODEL_NAME', 'gpt-4o')}")
print(f"  API Key set: {'✅' if os.getenv('GOOGLE_API_KEY') or os.getenv('OPENAI_API_KEY') else '❌'}")
print(f"  LangSmith Key set: {'✅' if os.getenv('LANGCHAIN_API_KEY') else '❌'}")
print("=" * 60)

from src.graph.workflow import build_workflow

# Default problem or from CLI args
DEFAULT_PROBLEM = "Place 4 queens on a 4×4 chessboard such that no two queens threaten each other. No two queens can share the same row, column, or diagonal."

# Check for local flag
args = sys.argv[1:]
is_local = False

if "-local" in args:
    is_local = True
    args.remove("-local")
elif "--local" in args:
    is_local = True
    args.remove("--local")

if is_local:
    os.environ["LLM_PROVIDER"] = "ollama"
    print("🚀 Local Mode Activated: Using Ollama (LangSmith tracing remains enabled if configured).\n")

problem = " ".join(args) if args else DEFAULT_PROBLEM

print(f"\n📝 Problem: {problem}\n")
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
}

# Stream with updates to see each agent step
if is_local:
    print("\n🚀 Running pipeline (Locally with Ollama, tracing → LangSmith)...\n")
else:
    print("\n🚀 Running pipeline (all traces → LangSmith)...\n")

for event in graph.stream(initial_state, stream_mode="updates"):
    for node_name, node_output in event.items():
        step = node_output.get("current_step", node_name)
        status = node_output.get("status", "")
        print(f"  ✅ [{node_name}] → {status}")

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
                print(f"     ⚠️  {issue}")

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

        print()

print("-" * 60)
print("✅ Pipeline complete! Check LangSmith for full traces:")
print("   https://smith.langchain.com")
print("-" * 60)
