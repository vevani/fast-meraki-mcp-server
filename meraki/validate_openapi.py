#!/usr/bin/env python3
"""
OpenAPI Specification Validator for Meraki MCP Server.

Validates the OpenAPI specification against GoFastMCP standards and best practices.
Ensures 100% compliance with MCP tool requirements.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set
from loguru import logger


class OpenAPIValidator:
    """Validates OpenAPI specification for MCP compliance."""
    
    def __init__(self, spec_path: Path):
        self.spec_path = spec_path
        self.spec: Dict[str, Any] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
    def load_spec(self) -> bool:
        """Load and parse the OpenAPI specification."""
        try:
            with open(self.spec_path, 'r', encoding='utf-8') as f:
                self.spec = json.load(f)
            return True
        except FileNotFoundError:
            self.errors.append(f"Specification file not found: {self.spec_path}")
            return False
        except json.JSONDecodeError as e:
            self.errors.append(f"Invalid JSON in specification: {e}")
            return False
    
    def validate_basic_structure(self) -> None:
        """Validate basic OpenAPI structure requirements."""
        required_fields = {
            'openapi': str,
            'info': dict,
            'paths': dict
        }
        
        for field, expected_type in required_fields.items():
            if field not in self.spec:
                self.errors.append(f"Missing required field: {field}")
            elif not isinstance(self.spec[field], expected_type):
                self.errors.append(f"Field '{field}' must be of type {expected_type.__name__}")
        
        # Validate OpenAPI version
        if 'openapi' in self.spec:
            version = self.spec['openapi']
            if not version.startswith('3.'):
                self.errors.append(f"OpenAPI version must be 3.x, got: {version}")
    
    def validate_info_section(self) -> None:
        """Validate the info section for completeness."""
        if 'info' not in self.spec:
            return
        
        info = self.spec['info']
        required_info_fields = ['title', 'version']
        recommended_info_fields = ['description', 'contact']
        
        for field in required_info_fields:
            if field not in info:
                self.errors.append(f"Missing required info field: {field}")
        
        for field in recommended_info_fields:
            if field not in info:
                self.warnings.append(f"Missing recommended info field: {field}")
    
    def validate_security_schemes(self) -> None:
        """Validate security scheme implementation."""
        components = self.spec.get('components', {})
        security_schemes = components.get('securitySchemes', {})
        
        if not security_schemes:
            self.errors.append("No security schemes defined")
            return
        
        # Check for proper API key scheme
        has_api_key = False
        for scheme_name, scheme in security_schemes.items():
            if scheme.get('type') == 'apiKey':
                has_api_key = True
                # Validate API key scheme structure
                required_fields = ['name', 'in']
                for field in required_fields:
                    if field not in scheme:
                        self.errors.append(f"Security scheme '{scheme_name}' missing field: {field}")
        
        if not has_api_key:
            self.warnings.append("No API key security scheme found")
        
        # Check if security is applied globally
        if 'security' not in self.spec:
            self.warnings.append("No global security requirements defined")
    
    def validate_operations(self) -> None:
        """Validate all operations for MCP compliance."""
        paths = self.spec.get('paths', {})
        
        total_operations = 0
        operations_without_summary = 0
        operations_without_description = 0
        operations_without_operation_id = 0
        operations_without_tags = 0
        operations_without_responses = 0
        
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
                
            for method, operation in methods.items():
                if not isinstance(operation, dict) or method.startswith('x-'):
                    continue
                
                total_operations += 1
                
                # Check required operation fields
                if 'operationId' not in operation:
                    operations_without_operation_id += 1
                    self.errors.append(f"Operation {method.upper()} {path} missing operationId")
                
                if 'summary' not in operation:
                    operations_without_summary += 1
                    self.warnings.append(f"Operation {method.upper()} {path} missing summary")
                
                if 'description' not in operation:
                    operations_without_description += 1
                    self.warnings.append(f"Operation {method.upper()} {path} missing description")
                
                if 'tags' not in operation:
                    operations_without_tags += 1
                    self.warnings.append(f"Operation {method.upper()} {path} missing tags")
                
                if 'responses' not in operation:
                    operations_without_responses += 1
                    self.errors.append(f"Operation {method.upper()} {path} missing responses")
                else:
                    self.validate_responses(operation['responses'], f"{method.upper()} {path}")
        
        logger.info(f"Validated {total_operations} operations")
        
        if operations_without_operation_id > 0:
            logger.error(f"{operations_without_operation_id} operations missing operationId")
        
        if operations_without_summary > 0:
            logger.warning(f"{operations_without_summary} operations missing summary")
        
        if operations_without_description > 0:
            logger.warning(f"{operations_without_description} operations missing description")
    
    def validate_responses(self, responses: Dict[str, Any], operation_name: str) -> None:
        """Validate response definitions."""
        if not responses:
            self.errors.append(f"Operation {operation_name} has no response definitions")
            return
        
        # Check for success response
        success_codes = {'200', '201', '202', '204'}
        has_success = any(code in responses for code in success_codes)
        
        if not has_success:
            self.warnings.append(f"Operation {operation_name} has no success response (2xx)")
        
        # Validate each response
        for status_code, response in responses.items():
            if isinstance(response, dict):
                if 'description' not in response:
                    self.errors.append(f"Response {status_code} in {operation_name} missing description")
    
    def validate_schemas(self) -> None:
        """Validate schema definitions for completeness."""
        components = self.spec.get('components', {})
        schemas = components.get('schemas', {})
        
        if not schemas:
            self.warnings.append("No schema definitions found")
            return
        
        logger.info(f"Found {len(schemas)} schema definitions")
        
        # Validate each schema
        for schema_name, schema in schemas.items():
            if not isinstance(schema, dict):
                continue
            
            # Check for description
            if 'description' not in schema:
                self.warnings.append(f"Schema '{schema_name}' missing description")
            
            # Check properties if it's an object
            if schema.get('type') == 'object' and 'properties' in schema:
                for prop_name, prop_def in schema['properties'].items():
                    if isinstance(prop_def, dict) and 'description' not in prop_def:
                        self.warnings.append(f"Property '{prop_name}' in schema '{schema_name}' missing description")
    
    def check_mcp_compliance(self) -> None:
        """Check specific MCP compliance requirements."""
        # MCP requires clear operation identification
        paths = self.spec.get('paths', {})
        operation_ids = set()
        
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            
            for method, operation in methods.items():
                if isinstance(operation, dict) and 'operationId' in operation:
                    op_id = operation['operationId']
                    if op_id in operation_ids:
                        self.errors.append(f"Duplicate operationId: {op_id}")
                    operation_ids.add(op_id)
        
        logger.info(f"Found {len(operation_ids)} unique operation IDs")
        
        # Check for consistent naming conventions
        inconsistent_naming = []
        for op_id in operation_ids:
            if not (op_id[0].islower() or op_id.startswith('get') or op_id.startswith('post') or 
                    op_id.startswith('put') or op_id.startswith('delete') or op_id.startswith('patch')):
                inconsistent_naming.append(op_id)
        
        if inconsistent_naming:
            self.warnings.append(f"Inconsistent operationId naming: {len(inconsistent_naming)} operations")
    
    def validate(self) -> bool:
        """Run complete validation and return success status."""
        logger.info(f"Validating OpenAPI specification: {self.spec_path}")
        
        if not self.load_spec():
            return False
        
        # Run all validation checks
        self.validate_basic_structure()
        self.validate_info_section()
        self.validate_security_schemes()
        self.validate_operations()
        self.validate_schemas()
        self.check_mcp_compliance()
        
        # Report results
        if self.errors:
            logger.error(f"Validation failed with {len(self.errors)} errors:")
            for error in self.errors:
                logger.error(f"  ❌ {error}")
        
        if self.warnings:
            logger.warning(f"Found {len(self.warnings)} warnings:")
            for warning in self.warnings:
                logger.warning(f"  ⚠️  {warning}")
        
        if not self.errors and not self.warnings:
            logger.success("✅ OpenAPI specification is fully compliant!")
        elif not self.errors:
            logger.info("✅ OpenAPI specification is valid with minor warnings")
        
        return len(self.errors) == 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            'valid': len(self.errors) == 0,
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'error_details': self.errors,
            'warning_details': self.warnings
        }


def main():
    """Main validation entry point."""
    spec_path = Path(__file__).parent / "openapi" / "spec3.json"
    
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, format="<level>{level}</level> | {message}")
    
    validator = OpenAPIValidator(spec_path)
    
    if validator.validate():
        logger.success("OpenAPI specification validation passed")
        sys.exit(0)
    else:
        logger.error("OpenAPI specification validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()