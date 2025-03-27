#!/usr/bin/env python3
"""
Simple test script for CPLEX optimization using DOcplex.
This script creates and solves a simple linear programming problem.
"""

from docplex.mp.model import Model

def create_and_solve_model():
    # Create a new model
    model = Model(name='production_planning')
    
    # Create decision variables
    x = model.continuous_var(name='x', lb=0)  # Product X
    y = model.continuous_var(name='y', lb=0)  # Product Y
    
    # Add constraints
    # Constraint on resource A
    model.add_constraint(50 * x + 24 * y <= 2400, 'resource_a')
    # Constraint on resource B
    model.add_constraint(30 * x + 33 * y <= 2100, 'resource_b')
    
    # Set objective function (maximize profit)
    model.maximize(80 * x + 90 * y)
    
    # Solve the model
    solution = model.solve()
    
    if solution:
        print("Solution status:", solution.solve_status)
        print(f"Optimal production plan: Product X = {solution[x]:.2f}, Product Y = {solution[y]:.2f}")
        print(f"Maximum profit: ${solution.objective_value:.2f}")
        
        # Constraints usage
        for ct in model.iter_constraints():
            slack = ct.slack_value
            usage = 100 * (1 - slack / ct.right_expr.constant)
            print(f"Resource {ct.name}: {usage:.1f}% utilized")
    else:
        print("No solution found")
    
    return solution

if __name__ == "__main__":
    print("Testing CPLEX optimization with docplex...")
    solution = create_and_solve_model() 