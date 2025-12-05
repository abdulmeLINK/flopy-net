"""
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
Condition Evaluator Module.

This module provides classes for evaluating policy conditions and expressions.
"""

import logging
from typing import Dict, Any, Tuple, Union

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    """Evaluates policy conditions and expressions."""
    
    def evaluate_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate a complex condition expression with enhanced logic.
        
        Args:
            condition: The condition string to evaluate
            context: Context variables
            parameters: Rule parameters for variable substitution
            
        Returns:
            Tuple of (condition_result, explanation)
        """
        try:
            # Only replace parameter placeholders with actual values, not context variables
            # Context variables will be resolved by _get_value with proper type conversion
            evaluated_condition = condition
            for param_key, param_value in parameters.items():
                # Only replace if it's a clear parameter placeholder (not a variable name)
                if param_key in evaluated_condition:
                    evaluated_condition = evaluated_condition.replace(param_key, str(param_value))
            
            # Handle common operators and expressions
            if " AND " in evaluated_condition:
                parts = evaluated_condition.split(" AND ")
                results = []
                for part in parts:
                    part_result, part_reason = self.evaluate_simple_condition(part.strip(), context, parameters)
                    results.append((part_result, part_reason))
                
                all_true = all(r[0] for r in results)
                reasons = [r[1] for r in results]
                return all_true, f"AND condition: {' AND '.join(reasons)}"
                
            elif " OR " in evaluated_condition:
                parts = evaluated_condition.split(" OR ")
                results = []
                for part in parts:
                    part_result, part_reason = self.evaluate_simple_condition(part.strip(), context, parameters)
                    results.append((part_result, part_reason))
                
                any_true = any(r[0] for r in results)
                reasons = [r[1] for r in results]
                return any_true, f"OR condition: {' OR '.join(reasons)}"
            
            else:
                return self.evaluate_simple_condition(evaluated_condition, context, parameters)
                
        except Exception as e:
            logger.error(f"Error evaluating condition '{condition}': {e}")
            return False, f"Condition evaluation error: {str(e)}"
    
    def evaluate_simple_condition(self, condition: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Evaluate a simple condition expression.
        
        Args:
            condition: Simple condition string (e.g., "x >= 5")
            context: Context variables
            parameters: Rule parameters
            
        Returns:
            Tuple of (result, explanation)
        """
        try:
            # Handle comparison operators
            operators = [">=", "<=", "==", "!=", ">", "<"]
            
            for op in operators:
                if op in condition:
                    left, right = condition.split(op, 1)
                    left = left.strip()
                    right = right.strip()
                    
                    # Get left value
                    left_val = self.get_value(left, context, parameters)
                    right_val = self.get_value(right, context, parameters)
                    
                    # Enhanced type handling for comparisons
                    try:
                        # For numeric comparisons, ensure both values are numeric
                        if op in [">", "<", ">=", "<="]:
                            left_val = self.ensure_numeric_type(left_val, left)
                            right_val = self.ensure_numeric_type(right_val, right)
                        
                        # Perform comparison
                        if op == ">=":
                            result = left_val >= right_val
                        elif op == "<=":
                            result = left_val <= right_val
                        elif op == "==":
                            result = left_val == right_val
                        elif op == "!=":
                            result = left_val != right_val
                        elif op == ">":
                            result = left_val > right_val
                        elif op == "<":
                            result = left_val < right_val
                        
                        return result, f"{left}({left_val}) {op} {right}({right_val}) = {result}"
                        
                    except (TypeError, ValueError) as e:
                        logger.warning(f"Type conversion failed for condition '{condition}': {e}. Left: {left_val} ({type(left_val)}), Right: {right_val} ({type(right_val)})")
                        # For type errors, try string comparison as fallback for == and !=
                        if op in ["==", "!="]:
                            str_left = str(left_val)
                            str_right = str(right_val)
                            if op == "==":
                                result = str_left == str_right
                            else:
                                result = str_left != str_right
                            return result, f"{left}('{str_left}') {op} {right}('{str_right}') = {result} (string comparison)"
                        else:
                            # For numeric comparisons that fail, return False
                            return False, f"Type comparison error: {left}({left_val}, {type(left_val)}) {op} {right}({right_val}, {type(right_val)})"
            
            # If no operator found, treat as boolean
            bool_val = self.get_value(condition, context, parameters)
            return bool(bool_val), f"{condition} = {bool_val}"
            
        except Exception as e:
            logger.error(f"Error evaluating simple condition '{condition}': {e}")
            return False, f"Simple condition error: {str(e)}"
    
    def get_value(self, expr: str, context: Dict[str, Any], parameters: Dict[str, Any]) -> Any:
        """
        Get the value of an expression from context or parameters with proper type conversion.
        
        Args:
            expr: Expression to evaluate
            context: Context variables
            parameters: Rule parameters
            
        Returns:
            The evaluated value with appropriate type conversion
        """
        expr = expr.strip()
        
        # First try to get from context
        if expr in context:
            value = context[expr]
            converted_value = self.convert_to_appropriate_type(value)
            # Only log if there's a type conversion issue
            if type(value) != type(converted_value):
                logger.debug(f"Type conversion for '{expr}': {value} ({type(value)}) -> {converted_value} ({type(converted_value)})")
            return converted_value
        
        # Then try to get from parameters
        if expr in parameters:
            value = parameters[expr]
            converted_value = self.convert_to_appropriate_type(value)
            # Only log if there's a type conversion issue
            if type(value) != type(converted_value):
                logger.debug(f"Type conversion for '{expr}': {value} ({type(value)}) -> {converted_value} ({type(converted_value)})")
            return converted_value
        
        # Finally try to convert the expression itself to a number
        converted_value = self.convert_to_appropriate_type(expr)
        # Only log if it's not a simple literal conversion
        if expr != str(converted_value):
            logger.debug(f"Literal conversion '{expr}' -> {converted_value} ({type(converted_value)})")
        return converted_value
    
    def convert_to_appropriate_type(self, value: Any) -> Any:
        """
        Convert a value to the most appropriate type (int, float, bool, or string).
        
        Args:
            value: The value to convert
            
        Returns:
            The value converted to the most appropriate type
        """
        # If it's already a number or boolean, return as-is
        if isinstance(value, (int, float, bool)):
            return value
        
        # If it's not a string, return as-is
        if not isinstance(value, str):
            return value
        
        # Try to convert string to appropriate type
        value_str = value.strip()
        
        # Handle empty strings
        if not value_str:
            return None
        
        # Handle boolean values
        if value_str.lower() in ('true', 'false'):
            return value_str.lower() == 'true'
        
        # Handle None/null values
        if value_str.lower() in ('none', 'null'):
            return None
        
        # Try to convert to number
        try:
            # Check if it looks like a float
            if '.' in value_str or 'e' in value_str.lower():
                converted = float(value_str)
                # Check for special float values
                if converted != converted:  # NaN check
                    logger.warning(f"Converted string '{value_str}' to NaN, returning 0")
                    return 0.0
                return converted
            else:
                # Try int first, then float if int fails
                try:
                    return int(value_str)
                except ValueError:
                    converted = float(value_str)
                    # Check for special float values
                    if converted != converted:  # NaN check
                        logger.warning(f"Converted string '{value_str}' to NaN, returning 0")
                        return 0.0
                    return converted
        except ValueError:
            # If conversion fails, return as string
            # Only log if it looks like it should have been a number
            if any(c.isdigit() for c in value_str):
                logger.debug(f"Could not convert '{value_str}' to numeric type, keeping as string")
            return value_str

    def ensure_numeric_type(self, value: Any, expr_name: str) -> Union[int, float]:
        """
        Ensure a value is numeric, converting if necessary.
        
        Args:
            value: The value to convert
            expr_name: Name of the expression for error reporting
            
        Returns:
            Numeric value (int or float)
            
        Raises:
            ValueError: If the value cannot be converted to a number
        """
        if isinstance(value, (int, float)):
            return value
        
        if isinstance(value, bool):
            return int(value)
        
        if isinstance(value, str):
            value_str = value.strip()
            
            # Handle special string values
            if value_str.lower() in ('true', '1'):
                return 1
            elif value_str.lower() in ('false', '0'):
                return 0
            elif value_str.lower() in ('none', 'null', ''):
                return 0
            
            # Try to convert to number
            try:
                if '.' in value_str or 'e' in value_str.lower():
                    return float(value_str)
                else:
                    return int(value_str)
            except ValueError:
                raise ValueError(f"Cannot convert '{value_str}' to numeric value for expression '{expr_name}'")
        
        # Try to convert other types
        try:
            return float(value)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot convert {type(value)} value '{value}' to numeric for expression '{expr_name}'")
