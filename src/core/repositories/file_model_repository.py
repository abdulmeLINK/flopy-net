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
File Model Repository

This module provides a file-based implementation of the model repository.
"""
import os
import json
import logging
import numpy as np
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.core.model.fl_model import FLModel
from src.core.interfaces.model_repository import IModelRepository


class FileModelRepository(IModelRepository):
    """
    A file-based implementation of the model repository.
    
    This repository stores FL models on the file system, with metadata
    in JSON format and model weights in a format suitable for the model type.
    """
    
    def __init__(self, base_dir: str = 'data/artifacts', enable_saving: bool = True):
        """
        Initialize the repository with a base directory.
        
        Args:
            base_dir: The base directory to store models in
            enable_saving: Whether to enable model saving to disk
        """
        self.base_dir = base_dir
        self.enable_saving = enable_saving
        if enable_saving:
            os.makedirs(base_dir, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def save_model(self, model: FLModel, version: Optional[str] = None) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: The model to save
            version: Optional version string
            
        Returns:
            Success status
        """
        # Skip saving if disabled
        if not self.enable_saving:
            self.logger.info(f"Model saving disabled, skipping save for {model.name}")
            return True
            
        try:
            # Create model directory
            model_dir = os.path.join(self.base_dir, model.name)
            os.makedirs(model_dir, exist_ok=True)
            
            # Determine version
            if version is None:
                version = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save metadata
            metadata_path = os.path.join(model_dir, f"{version}_metadata.json")
            
            # Convert numpy arrays in metadata to Python lists for JSON serialization
            serializable_metadata = self._make_serializable(model.metadata)
            
            with open(metadata_path, 'w') as f:
                json.dump(serializable_metadata, f, indent=2)
            
            # Save each weight array as a numpy file
            for i, weight in enumerate(model.weights):
                weight_path = os.path.join(model_dir, f"{version}_weights_{i}.npy")
                np.save(weight_path, weight)
            
            return True
        except Exception as e:
            self.logger.error(f"Error saving model: {str(e)}")
            return False
    
    def load_model(self, name: str, version: Optional[str] = None) -> Optional[FLModel]:
        """
        Load a model from the repository.
        
        Args:
            name: The name of the model to load
            version: Optional version string
            
        Returns:
            The loaded model, or None if not found
        """
        if not self.enable_saving:
            self.logger.warning(f"Model saving is disabled, cannot load model {name}")
            return None
            
        try:
            model_dir = os.path.join(self.base_dir, name)
            
            if not os.path.exists(model_dir):
                self.logger.warning(f"Model directory {model_dir} not found")
                return None
            
            # Find the correct version
            if version is None:
                # Find the latest version
                metadata_files = [f for f in os.listdir(model_dir) if f.endswith("_metadata.json")]
                if not metadata_files:
                    self.logger.warning(f"No metadata files found in {model_dir}")
                    return None
                
                # Sort by filename (which includes timestamp)
                metadata_files.sort(reverse=True)
                version = metadata_files[0].split("_metadata.json")[0]
            
            # Load metadata
            metadata_path = os.path.join(model_dir, f"{version}_metadata.json")
            if not os.path.exists(metadata_path):
                self.logger.warning(f"Metadata file {metadata_path} not found")
                return None
            
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)
            
            # Find and load weight files
            weight_files = [f for f in os.listdir(model_dir) if f.startswith(version) and f.endswith(".npy")]
            weight_files.sort()  # Ensure correct order
            
            weights = []
            for weight_file in weight_files:
                if "weights" in weight_file:
                    weight_path = os.path.join(model_dir, weight_file)
                    weights.append(np.load(weight_path))
            
            # Create and return model
            model = FLModel(name=name, weights=weights)
            model.metadata = metadata
            
            return model
        except Exception as e:
            self.logger.error(f"Error loading model: {str(e)}")
            return None
    
    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            name: The name of the model to delete
            version: Optional version string
            
        Returns:
            Success status
        """
        try:
            model_dir = os.path.join(self.base_dir, name)
            
            if not os.path.exists(model_dir):
                self.logger.warning(f"Model directory {model_dir} not found")
                return False
            
            if version is None:
                # Delete all versions
                import shutil
                shutil.rmtree(model_dir)
                return True
            
            # Delete specific version
            files_to_delete = [
                f for f in os.listdir(model_dir) 
                if f.startswith(version)
            ]
            
            for file in files_to_delete:
                os.remove(os.path.join(model_dir, file))
            
            return True
        except Exception as e:
            self.logger.error(f"Error deleting model: {str(e)}")
            return False
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List all models in the repository.
        
        Returns:
            List of model information dictionaries
        """
        try:
            if not os.path.exists(self.base_dir):
                return []
            
            models = []
            
            # Iterate through model directories
            for model_name in os.listdir(self.base_dir):
                model_dir = os.path.join(self.base_dir, model_name)
                
                if not os.path.isdir(model_dir):
                    continue
                
                # Find metadata files
                metadata_files = [f for f in os.listdir(model_dir) if f.endswith("_metadata.json")]
                
                for metadata_file in metadata_files:
                    version = metadata_file.split("_metadata.json")[0]
                    
                    # Load metadata
                    metadata_path = os.path.join(model_dir, metadata_file)
                    with open(metadata_path, 'r') as f:
                        metadata = json.load(f)
                    
                    # Add model info
                    models.append({
                        "name": model_name,
                        "version": version,
                        "metadata": metadata
                    })
            
            return models
        except Exception as e:
            self.logger.error(f"Error listing models: {str(e)}")
            return []
    
    def list_versions(self, model_name: str) -> List[Dict[str, Any]]:
        """
        List all versions of a model.
        
        Args:
            model_name: Name of the model
            
        Returns:
            List of version metadata dictionaries
        """
        try:
            model_dir = os.path.join(self.base_dir, model_name)
            
            if not os.path.exists(model_dir) or not os.path.isdir(model_dir):
                self.logger.warning(f"Model directory {model_dir} not found")
                return []
            
            versions = []
            
            # Find metadata files
            metadata_files = [f for f in os.listdir(model_dir) if f.endswith("_metadata.json")]
            
            for metadata_file in metadata_files:
                version = metadata_file.split("_metadata.json")[0]
                
                # Load metadata
                metadata_path = os.path.join(model_dir, metadata_file)
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                
                # Add version info
                versions.append({
                    "version": version,
                    "timestamp": metadata.get("timestamp", 
                                            datetime.fromtimestamp(
                                                os.path.getctime(metadata_path)
                                            ).isoformat()),
                    "metadata": metadata
                })
            
            # Sort by timestamp if available
            versions.sort(key=lambda v: v.get("timestamp", ""), reverse=True)
            
            return versions
        except Exception as e:
            self.logger.error(f"Error listing versions for model {model_name}: {str(e)}")
            return []
    
    def _make_serializable(self, obj):
        """
        Convert an object to a JSON serializable format.
        
        Args:
            obj: The object to convert
            
        Returns:
            JSON serializable object
        """
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(v) for v in obj]
        elif isinstance(obj, tuple):
            return tuple(self._make_serializable(v) for v in obj)
        else:
            return obj