"""
Model Service

This module provides services for managing federated learning models.
"""
import logging
from typing import Dict, Any, Optional, List

from src.domain.interfaces.fl_model_repository import IFLModelRepository
from src.domain.entities.fl_model import FLModel


class ModelService:
    """
    Model Service handles operations related to federated learning models.
    
    This class is responsible for:
    1. Model storage and retrieval
    2. Model versioning
    3. Model metadata management
    """
    
    def __init__(self, 
                 model_repository: IFLModelRepository,
                 logger: Optional[logging.Logger] = None):
        """
        Initialize the model service.
        
        Args:
            model_repository: Repository for storing and retrieving models
            logger: Logger instance
        """
        self.model_repository = model_repository
        self.logger = logger or logging.getLogger(__name__)
    
    def save_model(self, model: FLModel, version: Optional[str] = None) -> bool:
        """
        Save a model to the repository.
        
        Args:
            model: The model to save
            version: Optional version identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if version:
                model.metadata["version"] = version
            
            self.logger.info(f"Saving model {model.name} (version: {version or 'latest'})")
            result = self.model_repository.save_model(model)
            
            if result:
                self.logger.info(f"Model {model.name} saved successfully")
            else:
                self.logger.error(f"Failed to save model {model.name}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_name: str, version: Optional[str] = None) -> Optional[FLModel]:
        """
        Load a model from the repository.
        
        Args:
            model_name: Name of the model to load
            version: Optional version to load (defaults to latest)
            
        Returns:
            The loaded model, or None if not found
        """
        try:
            self.logger.info(f"Loading model {model_name} (version: {version or 'latest'})")
            model = self.model_repository.load_model(model_name, version)
            
            if model:
                self.logger.info(f"Model {model_name} loaded successfully")
            else:
                self.logger.warning(f"Model {model_name} not found")
            
            return model
        
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            return None
    
    def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in the repository.
        
        Returns:
            List of model metadata dictionaries
        """
        try:
            models = self.model_repository.list_models()
            self.logger.info(f"Listed {len(models)} models from repository")
            return models
        
        except Exception as e:
            self.logger.error(f"Error listing models: {e}")
            return []
    
    def delete_model(self, model_name: str, version: Optional[str] = None) -> bool:
        """
        Delete a model from the repository.
        
        Args:
            model_name: Name of the model to delete
            version: Optional version to delete (defaults to all versions)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Deleting model {model_name} (version: {version or 'all'})")
            result = self.model_repository.delete_model(model_name, version)
            
            if result:
                self.logger.info(f"Model {model_name} deleted successfully")
            else:
                self.logger.warning(f"Failed to delete model {model_name}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error deleting model: {e}")
            return False
    
    def update_model_metadata(self, model_name: str, metadata: Dict[str, Any], 
                             version: Optional[str] = None) -> bool:
        """
        Update metadata for a model.
        
        Args:
            model_name: Name of the model to update
            metadata: New metadata to apply
            version: Optional version to update (defaults to latest)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Updating metadata for model {model_name} (version: {version or 'latest'})")
            
            # Load the model
            model = self.model_repository.load_model(model_name, version)
            if not model:
                self.logger.warning(f"Model {model_name} not found")
                return False
            
            # Update metadata
            model.metadata.update(metadata)
            
            # Save the updated model
            result = self.model_repository.save_model(model)
            
            if result:
                self.logger.info(f"Metadata for model {model_name} updated successfully")
            else:
                self.logger.warning(f"Failed to update metadata for model {model_name}")
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error updating model metadata: {e}")
            return False
    
    def get_model_info(self, model_name: str, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get information about a model.
        
        Args:
            model_name: Name of the model
            version: Optional version (defaults to latest)
            
        Returns:
            Dictionary with model information, or None if not found
        """
        try:
            # Load the model
            model = self.model_repository.load_model(model_name, version)
            if not model:
                self.logger.warning(f"Model {model_name} not found")
                return None
            
            # Extract model info
            model_info = {
                "name": model.name,
                "version": model.metadata.get("version", "latest"),
                "size": model.get_size(),
                "created_at": model.metadata.get("created_at"),
                "updated_at": model.metadata.get("updated_at"),
                "parameters": model.get_parameter_count(),
                "type": model.get_type(),
                "metrics": model.metadata.get("metrics", {})
            }
            
            return model_info
        
        except Exception as e:
            self.logger.error(f"Error getting model info: {e}")
            return None 