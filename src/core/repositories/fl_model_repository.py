#!/usr/bin/env python3
"""
Copyright (c) 2025 Abdulmelik Saylan

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

"""
FL Model Repository Implementation

This module provides a file-based implementation of the model repository.
"""
import logging
import os
import json
import pickle
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading

from src.core.model.fl_model import FLModel
from src.core.interfaces.model_repository import IModelRepository


class FileModelRepository(IModelRepository):
    """
    A file-based implementation of the model repository.
    
    This repository stores FL models on the file system, with metadata
    in JSON format and model weights in a format suitable for the model type.
    """
    
    def __init__(self, storage_dir: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the repository.
        
        Args:
            storage_dir: Directory to store model files
            logger: Optional logger
        """
        self.storage_dir = storage_dir
        self.lock = threading.RLock()
        self.logger = logger or logging.getLogger(__name__)
        
        # Ensure storage directory exists
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
            self.logger.info(f"Created model storage directory: {storage_dir}")
    
    def save_model(self, model: FLModel) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: Model to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        with self.lock:
            try:
                # Create model directory if it doesn't exist
                model_dir = os.path.join(self.storage_dir, model.model_name)
                os.makedirs(model_dir, exist_ok=True)
                
                # Save model parameters
                params_file = os.path.join(model_dir, f"parameters.pkl")
                with open(params_file, 'wb') as f:
                    pickle.dump(model.parameters, f)
                
                # Save model metadata
                metadata = {
                    'model_name': model.model_name,
                    'version': model.version,
                    'created_at': model.created_at.isoformat() if model.created_at else None,
                    'metrics': model.metrics
                }
                
                metadata_file = os.path.join(model_dir, f"metadata.json")
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                self.logger.info(f"Saved model {model.model_name} (version {model.version})")
                return True
            except Exception as e:
                self.logger.error(f"Error saving model {model.model_name}: {e}")
                return False
    
    def get_model(self, model_name: str, version: Optional[int] = None) -> Optional[FLModel]:
        """
        Get a model from the repository.
        
        Args:
            model_name: Name of the model to get
            version: Optional version to get, defaults to latest
            
        Returns:
            Model if found, None otherwise
        """
        with self.lock:
            try:
                model_dir = os.path.join(self.storage_dir, model_name)
                if not os.path.exists(model_dir):
                    self.logger.warning(f"Model {model_name} not found")
                    return None
                
                # Get metadata
                metadata_file = os.path.join(model_dir, f"metadata.json")
                if not os.path.exists(metadata_file):
                    self.logger.warning(f"Metadata for model {model_name} not found")
                    return None
                
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                # Check version if specified
                if version is not None and metadata.get('version') != version:
                    self.logger.warning(f"Model {model_name} version {version} not found")
                    return None
                
                # Get parameters
                params_file = os.path.join(model_dir, f"parameters.pkl")
                if not os.path.exists(params_file):
                    self.logger.warning(f"Parameters for model {model_name} not found")
                    return None
                
                with open(params_file, 'rb') as f:
                    parameters = pickle.load(f)
                
                # Create model
                model = FLModel(
                    model_name=model_name,
                    parameters=parameters,
                    metrics=metadata.get('metrics', {})
                )
                
                # Set version from metadata
                if 'version' in metadata:
                    model.version = metadata['version']
                
                self.logger.info(f"Retrieved model {model_name} (version {model.version})")
                return model
            except Exception as e:
                self.logger.error(f"Error retrieving model {model_name}: {e}")
                return None
    
    def list_models(self) -> List[str]:
        """
        List all model names in the repository.
        
        Returns:
            List of model names
        """
        with self.lock:
            try:
                if not os.path.exists(self.storage_dir):
                    return []
                
                # List directories in storage dir, each one is a model
                models = [d for d in os.listdir(self.storage_dir) 
                         if os.path.isdir(os.path.join(self.storage_dir, d))]
                
                self.logger.debug(f"Listed {len(models)} models")
                return models
            except Exception as e:
                self.logger.error(f"Error listing models: {e}")
                return []
    
    def delete_model(self, model_name: str) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            model_name: Name of the model to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        with self.lock:
            try:
                model_dir = os.path.join(self.storage_dir, model_name)
                if not os.path.exists(model_dir):
                    self.logger.warning(f"Model {model_name} not found")
                    return False
                
                # Remove model directory and all files
                for file in os.listdir(model_dir):
                    os.remove(os.path.join(model_dir, file))
                
                os.rmdir(model_dir)
                
                self.logger.info(f"Deleted model {model_name}")
                return True
            except Exception as e:
                self.logger.error(f"Error deleting model {model_name}: {e}")
                return False 