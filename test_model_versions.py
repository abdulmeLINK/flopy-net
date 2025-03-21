#!/usr/bin/env python
"""
Test Model Repository Versions

This script tests the ability to list model versions from the repository.
"""
import os
import sys
from pprint import pprint

from src.infrastructure.repositories.file_model_repository import FileModelRepository

def main():
    """Main function to test model versions."""
    if len(sys.argv) > 1:
        model_dir = sys.argv[1]
    else:
        model_dir = 'models/simple_test'
    
    if len(sys.argv) > 2:
        model_name = sys.argv[2]
    else:
        model_name = 'simple_model'
    
    print(f"Testing model versions in {model_dir} for model {model_name}")
    
    # Create repository
    repo = FileModelRepository(model_dir)
    
    # List all models
    print("\nAll models:")
    models = repo.list_models()
    print(f"Found {len(models)} models")
    for model in models:
        print(f"- {model['name']} (version: {model['version']})")
    
    # List versions of the specific model
    print(f"\nVersions of {model_name}:")
    versions = repo.list_versions(model_name)
    print(f"Found {len(versions)} versions")
    for version in versions:
        print(f"- {version['version']} (timestamp: {version['timestamp']})")
        if 'round' in version['metadata']:
            print(f"  Round: {version['metadata']['round']}")
        if 'aggregation_round' in version['metadata']:
            print(f"  Aggregation Round: {version['metadata']['aggregation_round']}")
        if 'participating_clients' in version['metadata']:
            print(f"  Participating Clients: {version['metadata']['participating_clients']}")
    
    # Load the latest model
    print("\nLoading latest model:")
    model = repo.load_model(model_name)
    if model:
        print(f"Loaded model: {model.name}")
        print(f"Model has {len(model.weights)} weight arrays")
        print(f"Weight shapes: {[w.shape for w in model.weights]}")
        print("Metadata:")
        pprint(model.metadata)
    else:
        print("Failed to load model")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 