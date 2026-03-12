"""Formalizer Agent — converts natural language problems into structured CSP specifications."""

import json
from langchain_core.messages import HumanMessage, SystemMessage

from src.config import get_llm, invoke_structured_with_retry
from src.state import PipelineState, CSPSpecification
from src.prompts.formalizer import FORMALIZER_SYSTEM, FORMALIZER_HUMAN


def formalizer_node(state: PipelineState) -> dict:
    """LangGraph node: Formalize a natural language problem into a CSP specification."""
    llm = get_llm()

    # Use structured output for reliable parsing
    structured_llm = llm.with_structured_output(CSPSpecification)

    messages = [
        SystemMessage(content=FORMALIZER_SYSTEM),
        HumanMessage(content=FORMALIZER_HUMAN.format(
            problem_description=state["problem_description"]
        )),
    ]

    result: CSPSpecification = invoke_structured_with_retry(structured_llm, messages)

    return {
        "csp_spec": result.model_dump(),
        "current_step": "formalized",
        "status": "CSP specification created",
    }
