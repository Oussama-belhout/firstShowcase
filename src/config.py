"""Configuration and environment setup for the CSP Solver multi-agent system."""

import os
import time
from dotenv import load_dotenv

load_dotenv()


def get_llm(temperature: float | None = None, model: str | None = None):
    """Get configured LLM instance (supports Gemini, OpenAI, Groq, and Ollama)."""
    provider = os.getenv("LLM_PROVIDER", "gemini").lower()
    temp = temperature if temperature is not None else float(os.getenv("MODEL_TEMPERATURE", "0.1"))

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        
        # Check if the user defined a remote host, otherwise fallback
        base_url = os.getenv("OLLAMA_HOST")
        
        return ChatOllama(
            model=model or os.getenv("MODEL_NAME", "llama3.1"),
            temperature=temp,
            base_url=base_url if base_url else None
        )
    elif provider == "groq":
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=model or os.getenv("MODEL_NAME", "llama-3.3-70b-versatile"),
            temperature=temp,
            api_key=os.getenv("GROQ_API_KEY"),
            max_retries=6,
            timeout=120,
        )
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=model or os.getenv("MODEL_NAME", "gemini-2.0-flash"),
            temperature=temp,
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            max_retries=2,
            timeout=120,
        )
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model or os.getenv("MODEL_NAME", "gpt-4o"),
            temperature=temp,
            api_key=os.getenv("OPENAI_API_KEY"),
        )


def invoke_with_retry(llm, messages, max_retries=6, base_delay=20):
    """Invoke LLM with manual retry logic for rate limit errors."""
    for attempt in range(max_retries):
        try:
            return llm.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            if "resource_exhausted" in error_str or "rate" in error_str or "quota" in error_str or "429" in error_str:
                delay = base_delay * (attempt + 1)
                print(f"    ⏳ Rate limited (attempt {attempt + 1}/{max_retries}), waiting {delay}s...")
                time.sleep(delay)
            else:
                raise
    # Final attempt — let it raise
    return llm.invoke(messages)


def invoke_structured_with_retry(llm_structured, messages, max_retries=6, base_delay=20):
    """Invoke structured LLM with manual retry logic for rate limit errors."""
    for attempt in range(max_retries):
        try:
            return llm_structured.invoke(messages)
        except Exception as e:
            error_str = str(e).lower()
            if "resource_exhausted" in error_str or "rate" in error_str or "quota" in error_str or "429" in error_str:
                delay = base_delay * (attempt + 1)
                print(f"    ⏳ Rate limited (attempt {attempt + 1}/{max_retries}), waiting {delay}s...")
                time.sleep(delay)
            else:
                raise
    # Final attempt — let it raise
    return llm_structured.invoke(messages)


# Global settings
MAX_REFINEMENT_ITERATIONS = int(os.getenv("MAX_REFINEMENT_ITERATIONS", "3"))
SOLVER_TIMEOUT_SECONDS = int(os.getenv("SOLVER_TIMEOUT_SECONDS", "30"))

# Choco runner paths
CHOCO_RUNNER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "choco_runner")
GENERATED_MODELS_DIR = os.path.join(CHOCO_RUNNER_DIR, "generated_models")

# Ensure generated models directory exists
os.makedirs(GENERATED_MODELS_DIR, exist_ok=True)

