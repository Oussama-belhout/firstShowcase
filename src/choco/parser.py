"""Parser for Choco Solver output — extracts solutions, statistics, and monitor traces."""

import re


def parse_solver_output(stdout: str) -> dict:
    """
    Parse the stdout from a Choco solver execution.
    
    Expected output format:
        SOLUTION: var1=val1, var2=val2, ...
        MONITOR_SOLUTION: [...]
        ** Choco statistics **
        ...
    """
    result = {
        "has_solution": False,
        "solution": {},
        "solution_text": "",
        "statistics": {},
        "monitor_traces": [],
    }

    if not stdout:
        return result

    lines = stdout.strip().split("\n")

    for line in lines:
        line = line.strip()

        # Parse SOLUTION lines
        if line.startswith("SOLUTION:"):
            result["has_solution"] = True
            solution_str = line[len("SOLUTION:"):].strip()
            result["solution_text"] = solution_str
            
            # Parse key=value pairs
            pairs = re.findall(r'(\w+)\s*=\s*([^\s,]+)', solution_str)
            for key, value in pairs:
                try:
                    result["solution"][key] = int(value)
                except ValueError:
                    result["solution"][key] = value

        # Parse MONITOR lines
        elif line.startswith("MONITOR_"):
            result["monitor_traces"].append(line)

        # Parse Choco statistics
        elif "Solutions:" in line or "solution" in line.lower():
            match = re.search(r'Solutions?:\s*(\d+)', line, re.IGNORECASE)
            if match:
                result["statistics"]["solutions_found"] = int(match.group(1))
                if int(match.group(1)) > 0:
                    result["has_solution"] = True

        elif "Building" in line and "time" in line.lower():
            result["statistics"]["building_time"] = line.strip()

        elif "Resolution" in line or "Solving" in line:
            result["statistics"]["resolution_info"] = line.strip()

        elif "Nodes:" in line:
            match = re.search(r'Nodes:\s*(\d+)', line)
            if match:
                result["statistics"]["nodes"] = int(match.group(1))

        elif "Backtracks:" in line:
            match = re.search(r'Backtracks:\s*(\d+)', line)
            if match:
                result["statistics"]["backtracks"] = int(match.group(1))

        elif "Fails:" in line:
            match = re.search(r'Fails:\s*(\d+)', line)
            if match:
                result["statistics"]["fails"] = int(match.group(1))

        elif "Restarts:" in line:
            match = re.search(r'Restarts:\s*(\d+)', line)
            if match:
                result["statistics"]["restarts"] = int(match.group(1))

    # If we found statistics with solutions > 0 but no SOLUTION: line,
    # try to extract solution from raw output
    if result["has_solution"] and not result["solution"]:
        result["solution_text"] = stdout[:500]

    return result
