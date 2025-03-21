#!/usr/bin/env python
"""
Model Repository Cleanup Utility

This script identifies and handles models stored in legacy formats,
either migrating them to the new format or removing them.
"""
import os
import sys
import json
import shutil
import logging
import argparse
from datetime import datetime
from pathlib import Path

from src.infrastructure.repositories.file_model_repository import FileModelRepository
from src.domain.entities.fl_model import FLModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('model_cleanup')

def find_legacy_models(base_dir):
    """
    Find models stored in legacy formats.
    
    Args:
        base_dir: Base directory to search
        
    Returns:
        List of legacy model paths
    """
    legacy_models = []
    
    for model_dir in Path(base_dir).glob('*'):
        if not model_dir.is_dir():
            continue
            
        # Check for round_X directories (legacy format)
        for round_dir in model_dir.glob('round_*'):
            if round_dir.is_dir():
                model_json = round_dir / 'model.json'
                if model_json.exists():
                    legacy_models.append(model_json)
    
    return legacy_models

def migrate_legacy_model(model_json_path, repository):
    """
    Migrate a legacy model to the new format.
    
    Args:
        model_json_path: Path to the legacy model.json file
        repository: FileModelRepository instance
        
    Returns:
        Success status
    """
    try:
        # Parse model details from path
        model_dir = model_json_path.parent.parent
        model_name = model_dir.name
        version = model_json_path.parent.name
        
        logger.info(f"Migrating legacy model: {model_name} ({version})")
        
        # Load legacy model data
        with open(model_json_path, 'r') as f:
            model_data = json.load(f)
        
        # Load metadata if available
        metadata_path = model_json_path.parent / 'metadata.json'
        metadata = {}
        if metadata_path.exists():
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
        
        # Create new model instance
        # This is a simplified example - actual weights may be stored differently 
        # in legacy models and would need appropriate conversion
        model = FLModel(name=model_name, weights=[])
        model.metadata = metadata
        
        # Save in new format
        success = repository.save_model(model, version=version)
        
        return success
    except Exception as e:
        logger.error(f"Error migrating legacy model {model_json_path}: {e}")
        return False

def cleanup_legacy_models(base_dir, action='report'):
    """
    Clean up legacy model formats.
    
    Args:
        base_dir: Base directory containing models
        action: What to do with legacy models ('report', 'migrate', or 'delete')
        
    Returns:
        List of processed models
    """
    repository = FileModelRepository(base_dir)
    
    # Find legacy models
    legacy_models = find_legacy_models(base_dir)
    logger.info(f"Found {len(legacy_models)} legacy model(s)")
    
    if not legacy_models:
        return []
    
    processed = []
    
    for model_path in legacy_models:
        if action == 'report':
            logger.info(f"Legacy model: {model_path}")
            processed.append(str(model_path))
            
        elif action == 'migrate':
            if migrate_legacy_model(model_path, repository):
                logger.info(f"Successfully migrated {model_path}")
                processed.append(str(model_path))
            else:
                logger.error(f"Failed to migrate {model_path}")
                
        elif action == 'delete':
            try:
                # Delete the entire round directory
                round_dir = model_path.parent
                shutil.rmtree(round_dir)
                logger.info(f"Deleted legacy model directory: {round_dir}")
                processed.append(str(round_dir))
            except Exception as e:
                logger.error(f"Error deleting {round_dir}: {e}")
    
    return processed

def main():
    """Main function to run the cleanup utility."""
    parser = argparse.ArgumentParser(description='Clean up legacy model formats')
    parser.add_argument('--base-dir', type=str, default='models', 
                        help='Base directory containing models')
    parser.add_argument('--action', choices=['report', 'migrate', 'delete'], 
                        default='report',
                        help='Action to take for legacy models')
    
    args = parser.parse_args()
    
    logger.info(f"Starting model cleanup in {args.base_dir} with action: {args.action}")
    
    processed = cleanup_legacy_models(args.base_dir, args.action)
    
    logger.info(f"Cleanup completed. Processed {len(processed)} model(s)")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 