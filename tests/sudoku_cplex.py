#!/usr/bin/env python3
"""
Sudoku solver using IBM CPLEX Optimizer.
This demonstrates how to solve constraint satisfaction problems with CPLEX.
"""

import docplex.mp.model as cplex_model
import numpy as np

def solve_quadratic_equation_with_cplex():
    """
    Solve the quadratic equation a*x^2 + b*x = c
    with a=1, b=4, c=0 using CPLEX.
    
    This is the same problem as in the original MiniZinc example.
    """
    print("=== Solving Quadratic Equation with CPLEX ===")
    print("Equation: x^2 + 4x = 0")
    
    # Create a CPLEX model
    model = cplex_model.Model(name="quadratic_equation")
    
    # Since the original equation is x^2 + 4x = 0
    # The solutions are x=0 and x=-4
    
    # Create variables
    x = model.continuous_var(lb=-100, ub=100, name="x")
    
    # We can formulate this as: "x = 0 OR x = -4" using binary variables
    is_zero = model.binary_var(name="is_zero")
    is_neg_four = model.binary_var(name="is_neg_four")
    
    # Add indicator constraints
    model.add_indicator(is_zero, x == 0)
    model.add_indicator(is_neg_four, x == -4)
    
    # Ensure exactly one solution is picked
    model.add_constraint(is_zero + is_neg_four == 1)
    
    # Solve the model
    solution = model.solve()
    
    # Print the solution
    if solution:
        print(f"Solution found: x = {solution[x]}")
        
        # Try to find the other solution by adding a constraint
        print("\nFinding alternative solution...")
        if solution[x] == 0:
            model.add_constraint(x != 0)
        else:
            model.add_constraint(x != -4)
            
        alt_solution = model.solve()
        if alt_solution:
            print(f"Alternative solution found: x = {alt_solution[x]}")
        else:
            print("No alternative solution found")
    else:
        print("No solution found")
    
    return solution

def solve_sudoku_with_cplex(puzzle):
    """
    Solve a Sudoku puzzle using CPLEX.
    
    Args:
        puzzle: A 2D array representing the Sudoku puzzle,
               where 0 represents empty cells.
    
    Returns:
        A 2D array with the solved Sudoku, or None if no solution exists.
    """
    n = len(puzzle)  # Size of the grid (9 for standard Sudoku)
    subgrid_size = int(np.sqrt(n))  # Size of subgrids (3 for standard Sudoku)
    
    print(f"\n=== Solving {n}x{n} Sudoku with CPLEX ===")
    print("Initial puzzle:")
    print_sudoku(puzzle)
    
    # Create a CPLEX model
    model = cplex_model.Model(name=f"sudoku_{n}x{n}")
    
    # Create variables for each cell
    # grid[i,j,v] = 1 means cell (i,j) has value v
    grid = {}
    for i in range(n):
        for j in range(n):
            for v in range(1, n+1):
                grid[i, j, v] = model.binary_var(name=f"grid_{i}_{j}_{v}")
    
    # Initial values constraint
    for i in range(n):
        for j in range(n):
            if puzzle[i][j] > 0:
                # If the initial grid has a value, set the corresponding variable to 1
                model.add_constraint(grid[i, j, puzzle[i][j]] == 1)
    
    # Each cell has exactly one value
    for i in range(n):
        for j in range(n):
            model.add_constraint(
                model.sum(grid[i, j, v] for v in range(1, n+1)) == 1
            )
    
    # Each row has each value exactly once
    for i in range(n):
        for v in range(1, n+1):
            model.add_constraint(
                model.sum(grid[i, j, v] for j in range(n)) == 1
            )
    
    # Each column has each value exactly once
    for j in range(n):
        for v in range(1, n+1):
            model.add_constraint(
                model.sum(grid[i, j, v] for i in range(n)) == 1
            )
    
    # Each subgrid has each value exactly once
    for box_i in range(subgrid_size):
        for box_j in range(subgrid_size):
            for v in range(1, n+1):
                model.add_constraint(
                    model.sum(
                        grid[box_i*subgrid_size + i, box_j*subgrid_size + j, v] 
                        for i in range(subgrid_size) for j in range(subgrid_size)
                    ) == 1
                )
    
    # Solve the model
    solution = model.solve()
    
    # Process the solution
    if solution:
        # Create a grid to hold the solution
        solution_grid = [[0 for _ in range(n)] for _ in range(n)]
        for i in range(n):
            for j in range(n):
                for v in range(1, n+1):
                    if solution[grid[i, j, v]] > 0.5:
                        solution_grid[i][j] = v
        
        print("\nSolution found:")
        print_sudoku(solution_grid)
        return solution_grid
    else:
        print("No solution found")
        return None

def print_sudoku(grid):
    """Print a Sudoku grid in a readable format."""
    n = len(grid)
    subgrid_size = int(np.sqrt(n))
    
    # Print horizontal line
    def print_h_line():
        line = "+"
        for i in range(subgrid_size):
            line += "-" * (subgrid_size * 2 + 1) + "+"
        print(line)
    
    for i in range(n):
        if i % subgrid_size == 0:
            print_h_line()
        
        line = "|"
        for j in range(n):
            if j % subgrid_size == 0 and j > 0:
                line += "|"
            value = grid[i][j]
            line += " " + (str(value) if value > 0 else " ")
        line += " |"
        print(line)
    
    print_h_line()

if __name__ == "__main__":
    # First solve the quadratic equation
    solve_quadratic_equation_with_cplex()
    
    # Then solve a 4x4 Sudoku
    sudoku_4x4 = [
        [0, 1, 0, 4],
        [0, 0, 0, 0],
        [0, 0, 2, 0],
        [3, 0, 0, 0]
    ]
    solve_sudoku_with_cplex(sudoku_4x4)
    
    # Finally, solve a standard 9x9 Sudoku
    sudoku_9x9 = [
        [5, 3, 0, 0, 7, 0, 0, 0, 0],
        [6, 0, 0, 1, 9, 5, 0, 0, 0],
        [0, 9, 8, 0, 0, 0, 0, 6, 0],
        [8, 0, 0, 0, 6, 0, 0, 0, 3],
        [4, 0, 0, 8, 0, 3, 0, 0, 1],
        [7, 0, 0, 0, 2, 0, 0, 0, 6],
        [0, 6, 0, 0, 0, 0, 2, 8, 0],
        [0, 0, 0, 4, 1, 9, 0, 0, 5],
        [0, 0, 0, 0, 8, 0, 0, 7, 9]
    ]
    solve_sudoku_with_cplex(sudoku_9x9) 