#!/usr/bin/env python3
"""
Script to run the test functions in the test_classification.py file.
"""

import os
import sys
import argparse
from test_classification import test_classification_system, test_mlflow, create_test_experiment

def main():
    """Run tests based on the command line arguments."""
    parser = argparse.ArgumentParser(description="Run classification tests.")
    parser.add_argument(
        "--test", 
        choices=["classification", "mlflow", "experiment", "unittest"],
        help="Which test to run"
    )
    
    args = parser.parse_args()
    
    if args.test == "classification":
        print("Running classification system test...")
        test_classification_system()
    elif args.test == "mlflow":
        print("Testing MLflow configuration...")
        if test_mlflow():
            print("MLflow test successful! MLflow is configured and ready.")
        else:
            print("MLflow test failed. Check logs for details.")
    elif args.test == "experiment":
        print("Creating test data for MLflow experiment...")
        create_test_experiment()
        print("Test complete. Check MLflow UI to see the logged data.")
    elif args.test == "unittest":
        import unittest
        from test_classification import TestClassification
        suite = unittest.TestLoader().loadTestsFromTestCase(TestClassification)
        unittest.TextTestRunner(verbosity=2).run(suite)
    else:
        # By default, run a basic test
        print("No test specified. Running basic classification test...")
        # Add parent directory to path to import classification module
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        import classification
        
        # Configure DSPy
        lm = classification.configure_dspy()
        if not lm:
            print("Failed to configure DSPy. Test cannot continue.")
            return
        
        # Test a simple classification
        test_event = "Weekly team meeting with engineering"
        print(f"Classifying test event: '{test_event}'")
        project_id, confidence = classification.classify_event(test_event, lm=lm)
        
        if project_id is not None:
            print(f"Classification result: Project ID {project_id}, Confidence {confidence:.2f}%")
        else:
            print(f"Classification result: Unknown (no project assigned), Confidence {confidence:.2f}%")

if __name__ == "__main__":
    main() 