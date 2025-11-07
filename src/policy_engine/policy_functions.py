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
Policy Functions Module

This module provides classes for managing, validating and executing policy functions.
"""

import os
import json
import logging
import time
import uuid
import importlib.util
import inspect
from typing import Dict, Any, List, Optional, Union, Callable

logger = logging.getLogger(__name__)

class PolicyFunctionError(Exception):
    """Exception raised for errors related to policy functions."""
    pass

class PolicyFunction:
    """
    Represents a function that can be used in policy evaluation.
    """
    
    def __init__(self, function_id: str, name: str, code: str, description: str = "", metadata: Dict[str, Any] = None):
        """
        Initialize a policy function.
        
        Args:
            function_id: Unique identifier for the function
            name: Name of the function
            code: Python code for the function
            description: Optional description
            metadata: Optional metadata dictionary
        """
        self.id = function_id
        self.name = name
        self.code = code
        self.description = description
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.updated_at = time.time()
        self._compiled_function = None
        
        # Validate and compile the function code
        self._compile_function()
        
        logger.debug(f"Initialized policy function {self.id}: {self.name}")
    
    def _compile_function(self) -> None:
        """
        Compile the function code into a callable.
        
        Raises:
            PolicyFunctionError: If the function code is invalid
        """
        try:
            # Create a namespace for the function
            namespace = {}
            
            # Add the code to the namespace
            exec(self.code, namespace)
            
            # Find the main function in the namespace
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith('_'):
                    self._compiled_function = obj
                    break
            
            # If no function was found, raise an error
            if self._compiled_function is None:
                raise PolicyFunctionError("No function found in the code")
                
            # Check if the function accepts a context parameter
            sig = inspect.signature(self._compiled_function)
            if 'context' not in sig.parameters:
                raise PolicyFunctionError("Function must accept a 'context' parameter")
                
        except Exception as e:
            logger.error(f"Error compiling function {self.name}: {str(e)}")
            raise PolicyFunctionError(f"Error compiling function: {str(e)}")
    
    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute the function with the given context.
        
        Args:
            context: Context for the function execution
            
        Returns:
            The function result
            
        Raises:
            PolicyFunctionError: If the function execution fails
        """
        if self._compiled_function is None:
            raise PolicyFunctionError("Function not compiled")
            
        try:
            return self._compiled_function(context)
        except Exception as e:
            logger.error(f"Error executing function {self.name}: {str(e)}")
            raise PolicyFunctionError(f"Error executing function: {str(e)}")

    def evaluate(self, context: Dict[str, Any]) -> Any:
        """
        Alias for execute method for backward compatibility.
        
        Args:
            context: Context for the function evaluation
            
        Returns:
            The function result
            
        Raises:
            PolicyFunctionError: If the function execution fails
        """
        return self.execute(context)


class PolicyFunctionManager:
    """
    Manages a collection of policy functions.
    """
    
    def __init__(self, functions_dir: Optional[str] = None):
        """
        Initialize the policy function manager.
        
        Args:
            functions_dir: Directory containing policy function files
        """
        self.functions: Dict[str, PolicyFunction] = {}
        self.functions_dir = functions_dir
        
        # Load functions if directory is provided
        if functions_dir:
            self.load_functions(functions_dir)
        
        logger.info(f"Initialized PolicyFunctionManager with {len(self.functions)} functions")
    
    def load_functions(self, functions_dir: Optional[str] = None) -> bool:
        """
        Load functions from a directory.
        
        Args:
            functions_dir: Directory containing policy function files
            
        Returns:
            True if functions were loaded successfully, False otherwise
        """
        dir_path = functions_dir or self.functions_dir
        if not dir_path:
            logger.warning("No functions directory specified")
            return False
        
        try:
            if os.path.exists(dir_path) and os.path.isdir(dir_path):
                # Clear existing functions
                self.functions = {}
                
                # Load functions from files
                for filename in os.listdir(dir_path):
                    if filename.endswith('.py') or filename.endswith('.json'):
                        file_path = os.path.join(dir_path, filename)
                        
                        try:
                            # JSON files contain function metadata
                            if filename.endswith('.json'):
                                with open(file_path, 'r') as f:
                                    data = json.load(f)
                                    
                                # Get function attributes
                                function_id = data.get('id', str(uuid.uuid4()))
                                name = data.get('name', os.path.splitext(filename)[0])
                                
                                # Find the corresponding Python file
                                py_file = os.path.join(dir_path, f"{os.path.splitext(filename)[0]}.py")
                                if not os.path.exists(py_file):
                                    logger.warning(f"Python file not found for {filename}")
                                    continue
                                    
                                # Load the code
                                with open(py_file, 'r') as f:
                                    code = f.read()
                                    
                                # Create function
                                self.functions[function_id] = PolicyFunction(
                                    function_id,
                                    name,
                                    code,
                                    data.get('description', ''),
                                    data.get('metadata', {})
                                )
                                
                            # Python files are standalone functions
                            elif filename.endswith('.py'):
                                # Check if there's a JSON file with the same name
                                json_file = os.path.join(dir_path, f"{os.path.splitext(filename)[0]}.json")
                                if os.path.exists(json_file):
                                    # Skip, it will be loaded with the JSON file
                                    continue
                                    
                                # Load the code
                                with open(file_path, 'r') as f:
                                    code = f.read()
                                    
                                # Create function with default attributes
                                function_id = str(uuid.uuid4())
                                name = os.path.splitext(filename)[0]
                                
                                self.functions[function_id] = PolicyFunction(
                                    function_id,
                                    name,
                                    code
                                )
                                
                        except Exception as e:
                            logger.error(f"Error loading function from {filename}: {str(e)}")
                
                logger.info(f"Loaded {len(self.functions)} functions from {dir_path}")
                return True
            else:
                logger.warning(f"Functions directory not found: {dir_path}")
                return False
        except Exception as e:
            logger.error(f"Error loading functions: {str(e)}")
            return False
    
    def save_functions(self, functions_dir: Optional[str] = None) -> bool:
        """
        Save functions to a directory.
        
        Args:
            functions_dir: Directory to save policy function files
            
        Returns:
            True if functions were saved successfully, False otherwise
        """
        dir_path = functions_dir or self.functions_dir
        if not dir_path:
            logger.warning("No functions directory specified")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(dir_path, exist_ok=True)
            
            # Save each function
            for function_id, function in self.functions.items():
                # Create a base filename from the function name
                base_filename = function.name.lower().replace(' ', '_')
                
                # Save the code to a Python file
                py_file = os.path.join(dir_path, f"{base_filename}.py")
                with open(py_file, 'w') as f:
                    f.write(function.code)
                
                # Save the metadata to a JSON file
                json_file = os.path.join(dir_path, f"{base_filename}.json")
                with open(json_file, 'w') as f:
                    json.dump({
                        'id': function.id,
                        'name': function.name,
                        'description': function.description,
                        'metadata': function.metadata,
                        'created_at': function.created_at,
                        'updated_at': function.updated_at
                    }, f, indent=2)
            
            logger.info(f"Saved {len(self.functions)} functions to {dir_path}")
            return True
        except Exception as e:
            logger.error(f"Error saving functions: {str(e)}")
            return False
    
    def add_function(self, name: str, code: str, description: str = "", metadata: Dict[str, Any] = None) -> Optional[str]:
        """
        Add a new policy function.
        
        Args:
            name: Name of the function
            code: Python code for the function
            description: Optional description
            metadata: Optional metadata dictionary
            
        Returns:
            Function ID if successful, None otherwise
        """
        try:
            # Validate the function code
            self.validate_function_code(code)
            
            # Create a new function
            function_id = str(uuid.uuid4())
            self.functions[function_id] = PolicyFunction(
                function_id,
                name,
                code,
                description,
                metadata
            )
            
            logger.info(f"Added function {function_id}: {name}")
            return function_id
        except Exception as e:
            logger.error(f"Error adding function: {str(e)}")
            return None
    
    def get_function(self, function_id: str) -> Optional[PolicyFunction]:
        """
        Get a function by ID.
        
        Args:
            function_id: ID of the function to retrieve
            
        Returns:
            PolicyFunction if found, None otherwise
        """
        return self.functions.get(function_id)
    
    def update_function(self, function_id: str, name: Optional[str] = None, code: Optional[str] = None,
                       description: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update an existing policy function.
        
        Args:
            function_id: Function ID
            name: New name (optional)
            code: New code (optional)
            description: New description (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if successful, False otherwise
        """
        if function_id not in self.functions:
            logger.warning(f"Function {function_id} not found")
            return False
        
        try:
            function = self.functions[function_id]
            
            # Update code if provided (and validate it)
            if code:
                self.validate_function_code(code)
                function.code = code
                function._compile_function()
            
            # Update other attributes if provided
            if name:
                function.name = name
            
            if description is not None:
                function.description = description
                
            if metadata is not None:
                function.metadata = metadata
                
            # Update timestamp
            function.updated_at = time.time()
            
            logger.info(f"Updated function {function_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating function {function_id}: {str(e)}")
            return False
    
    def delete_function(self, function_id: str) -> bool:
        """
        Delete a policy function.
        
        Args:
            function_id: Function ID
            
        Returns:
            True if successful, False otherwise
        """
        if function_id not in self.functions:
            logger.warning(f"Function {function_id} not found")
            return False
        
        try:
            del self.functions[function_id]
            logger.info(f"Deleted function {function_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting function {function_id}: {str(e)}")
            return False
    
    def validate_function_code(self, code: str) -> Dict[str, Any]:
        """
        Validate the Python code for a policy function.
        
        Args:
            code: Python code to validate
            
        Returns:
            Dictionary with validation results
            
        Raises:
            PolicyFunctionError: If the code is invalid
        """
        try:
            # Try to compile the code to check for syntax errors
            compile(code, '<string>', 'exec')
            
            # Create a namespace for the function
            namespace = {}
            
            # Try to execute the code
            exec(code, namespace)
            
            # Find callable objects in the namespace
            functions = []
            for name, obj in namespace.items():
                if callable(obj) and not name.startswith('_'):
                    functions.append(name)
            
            if not functions:
                raise PolicyFunctionError("No function found in the code")
                
            # Check if the main function accepts a context parameter
            main_function = namespace[functions[0]]
            sig = inspect.signature(main_function)
            
            if 'context' not in sig.parameters:
                raise PolicyFunctionError("Function must accept a 'context' parameter")
                
            return {
                'valid': True,
                'message': 'Function code is valid',
                'functions': functions
            }
                
        except Exception as e:
            logger.error(f"Error validating function code: {str(e)}")
            raise PolicyFunctionError(f"Error validating function code: {str(e)}")
    
    def execute_function(self, function_id: str, context: Dict[str, Any]) -> Any:
        """
        Execute a policy function with the given context.
        
        Args:
            function_id: Function ID
            context: Context for the function execution
            
        Returns:
            The function result
            
        Raises:
            PolicyFunctionError: If the function does not exist or execution fails
        """
        if function_id not in self.functions:
            raise PolicyFunctionError(f"Function {function_id} not found")
            
        function = self.functions[function_id]
        return function.execute(context)
    
    def evaluate_function(self, function_id: str, context: Dict[str, Any]) -> Any:
        """
        Alias for execute_function method for backward compatibility.
        
        Args:
            function_id: Function ID
            context: Context for the function evaluation
            
        Returns:
            The function result
            
        Raises:
            PolicyFunctionError: If the function does not exist or evaluation fails
        """
        return self.execute_function(function_id, context)
    
    def test_function(self, code: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test a function code with a given context.
        
        Args:
            code: Python code to test
            context: Context for the function execution
            
        Returns:
            Dictionary with test results
        """
        try:
            # Validate the function code
            validation = self.validate_function_code(code)
            
            # Create a temporary function
            temp_function = PolicyFunction(
                'temp',
                'temp',
                code
            )
            
            # Execute the function
            result = temp_function.execute(context)
            
            return {
                'success': True,
                'result': result,
                'message': 'Function executed successfully'
            }
        except Exception as e:
            logger.error(f"Error testing function: {str(e)}")
            return {
                'success': False,
                'result': None,
                'message': str(e)
            }
    
    def list_functions(self) -> List[Dict[str, Any]]:
        """
        List all available functions.
        
        Returns:
            List of function information dictionaries
        """
        function_list = []
        for function_id, function in self.functions.items():
            function_list.append({
                "id": function.id,
                "name": function.name,
                "description": function.description,
                "metadata": function.metadata,
                "created_at": function.created_at,
                "updated_at": function.updated_at
            })
        return function_list 