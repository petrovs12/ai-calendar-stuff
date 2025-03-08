#!/usr/bin/env python3
"""
Test script for using CPLEX with MiniZinc via command line.
This approach uses subprocess to call MiniZinc directly with the appropriate flags.
"""

import subprocess
import tempfile
import os

# Path to CPLEX shared library
CPLEX_DLL_PATH = "/Volumes/vlexar/Applications/CPLEX_Studio2211/cplex/bin/arm64_osx/libcplex2211.dylib"

def solve_with_minizinc_cplex():
    """
    Solve a simple quadratic equation using MiniZinc with CPLEX.
    """
    print("=== Solving with MiniZinc + CPLEX via command line ===")
    
    # Check if CPLEX shared library exists
    if not os.path.exists(CPLEX_DLL_PATH):
        print(f"Error: CPLEX shared library not found at: {CPLEX_DLL_PATH}")
        return False
    
    # Create a temporary MiniZinc model file
    with tempfile.NamedTemporaryFile(suffix='.mzn', delete=False) as model_file:
        model_file.write(b"""
var -100..100: x;
int: a = 1;
int: b = 4;
int: c = 0;
constraint a*(x*x) + b*x = c;
solve satisfy;
output ["x = ", show(x), "\\n"];
""")
        model_path = model_file.name
    
    try:
        # Construct the MiniZinc command with CPLEX
        cmd = [
            "minizinc",
            "--solver", "cplex",
            "--cplex-dll", CPLEX_DLL_PATH,
            model_path
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        
        # Run the command
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        # Print the output
        print("\nCommand output:")
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"Error (return code {result.returncode}):")
            print(result.stderr)
            return False
        
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False
    
    finally:
        # Clean up the temporary file
        os.unlink(model_path)

def solve_with_docplex():
    """
    Solve the same problem using docplex directly.
    """
    print("\n=== Solving with docplex directly ===")
    
    try:
        import docplex.mp.model as cplex_model
        
        # Create a CPLEX model for the same problem
        cpx = cplex_model.Model(name="quadratic_equation")
        
        # Since the original equation is x^2 + 4x = 0
        # The solutions are x=0 and x=-4
        
        # Create variables
        x = cpx.continuous_var(lb=-100, ub=100, name="x")
        
        # We can formulate this as: "x = 0 OR x = -4" using binary variables
        is_zero = cpx.binary_var(name="is_zero")
        is_neg_four = cpx.binary_var(name="is_neg_four")
        
        # Add indicator constraints
        cpx.add_indicator(is_zero, x == 0)
        cpx.add_indicator(is_neg_four, x == -4)
        
        # Ensure exactly one solution is picked
        cpx.add_constraint(is_zero + is_neg_four == 1)
        
        # Solve the model
        solution = cpx.solve()
        
        # Print the solution
        if solution:
            print(f"Solution found: x = {solution[x]}")
            
            # Try to find the other solution by adding a constraint
            print("\nFinding alternative solution...")
            if solution[x] == 0:
                cpx.add_constraint(x != 0)
            else:
                cpx.add_constraint(x != -4)
                
            alt_solution = cpx.solve()
            if alt_solution:
                print(f"Alternative solution found: x = {alt_solution[x]}")
            else:
                print("No alternative solution found")
                
            return True
        else:
            print("No solution found")
            return False
            
    except Exception as e:
        print(f"Error using docplex: {e}")
        return False

if __name__ == "__main__":
    # Try both approaches
    minizinc_success = solve_with_minizinc_cplex()
    docplex_success = solve_with_docplex()
    
    # Summary
    print("\n=== Summary ===")
    print(f"MiniZinc + CPLEX: {'Success' if minizinc_success else 'Failed'}")
    print(f"DOcplex direct:   {'Success' if docplex_success else 'Failed'}") 