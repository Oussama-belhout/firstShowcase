"""Choco Solver subprocess bridge — compiles and runs generated Java code."""

import os
import subprocess
import shutil
from src.config import CHOCO_RUNNER_DIR, GENERATED_MODELS_DIR, SOLVER_TIMEOUT_SECONDS


def compile_and_run_model(java_code: str, class_name: str) -> dict:
    """
    Compile and run a Choco Solver Java model.
    
    1. Writes the Java source to choco_runner/generated_models/
    2. Compiles with Maven
    3. Runs the compiled class
    4. Returns stdout, stderr, and status
    """
    result = {
        "status": "unknown",
        "stdout": "",
        "stderr": "",
    }

    # Write the Java source file
    source_dir = os.path.join(CHOCO_RUNNER_DIR, "src", "main", "java", "runner")
    os.makedirs(source_dir, exist_ok=True)
    
    source_file = os.path.join(source_dir, f"{class_name}.java")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(java_code)

    # Also save a copy to generated_models for reference
    backup_file = os.path.join(GENERATED_MODELS_DIR, f"{class_name}.java")
    os.makedirs(GENERATED_MODELS_DIR, exist_ok=True)
    shutil.copy2(source_file, backup_file)

    # Step 1: Compile with Maven
    try:
        compile_proc = subprocess.run(
            ["mvn", "compile", "-q"],
            cwd=CHOCO_RUNNER_DIR,
            capture_output=True,
            text=True,
            timeout=60,
            shell=True,
        )
        
        if compile_proc.returncode != 0:
            result["status"] = "compilation_error"
            result["stderr"] = compile_proc.stderr
            result["stdout"] = compile_proc.stdout
            return result
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["stderr"] = "Compilation timed out after 60s"
        return result
    except FileNotFoundError:
        result["status"] = "compilation_error"
        result["stderr"] = "Maven (mvn) not found. Please install Maven and ensure it's on your PATH."
        return result

    # Step 2: Run the compiled class
    try:
        run_proc = subprocess.run(
            [
                "mvn", "exec:java",
                f"-Dexec.mainClass=runner.{class_name}",
                "-q",
            ],
            cwd=CHOCO_RUNNER_DIR,
            capture_output=True,
            text=True,
            timeout=SOLVER_TIMEOUT_SECONDS,
            shell=True,
        )
        
        result["stdout"] = run_proc.stdout
        result["stderr"] = run_proc.stderr
        
        if run_proc.returncode != 0:
            result["status"] = "runtime_error"
        else:
            result["status"] = "success"
            
    except subprocess.TimeoutExpired:
        result["status"] = "timeout"
        result["stderr"] = f"Solver timed out after {SOLVER_TIMEOUT_SECONDS}s"
    except Exception as e:
        result["status"] = "runtime_error"
        result["stderr"] = str(e)

    return result
