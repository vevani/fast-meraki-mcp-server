#!/usr/bin/env python3
"""
Simple compliance validator for Meraki MCP Server.
Tests basic structure without external dependencies.
"""

import os
import sys
import json
from pathlib import Path


def log_result(test_name: str, passed: bool, message: str = ""):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {test_name}")
    if not passed and message:
        print(f"    Error: {message}")


def test_file_structure():
    """Test that all required files are present."""
    print("\n=== Testing File Structure ===")
    
    required_files = [
        '__init__.py',
        'meraki_mcp_server.py',
        'health_check.py',
        'validate_openapi.py',
        'test_compliance.py',
        'requirements.txt',
        'Dockerfile',
        '.env.example',
        'openapi/spec3.json'
    ]
    
    all_passed = True
    for file_path in required_files:
        full_path = Path(__file__).parent / file_path
        exists = full_path.exists()
        log_result(f"File exists: {file_path}", exists, f"Missing: {full_path}")
        if not exists:
            all_passed = False
    
    return all_passed


def test_openapi_spec():
    """Test OpenAPI specification."""
    print("\n=== Testing OpenAPI Specification ===")
    
    spec_path = Path(__file__).parent / "openapi" / "spec3.json"
    all_passed = True
    
    try:
        with open(spec_path, 'r', encoding='utf-8') as f:
            spec = json.load(f)
        
        log_result("OpenAPI spec loads as valid JSON", True)
        
        # Test basic structure
        required_fields = ['openapi', 'info', 'paths']
        for field in required_fields:
            exists = field in spec
            log_result(f"Has required field: {field}", exists)
            if not exists:
                all_passed = False
        
        # Test version
        if 'openapi' in spec:
            version_valid = spec['openapi'].startswith('3.')
            log_result(f"OpenAPI version 3.x: {spec['openapi']}", version_valid)
            if not version_valid:
                all_passed = False
        
        # Test paths count
        if 'paths' in spec:
            paths_count = len(spec['paths'])
            has_paths = paths_count > 0
            log_result(f"Has API paths: {paths_count} paths", has_paths)
            if not has_paths:
                all_passed = False
        
        # Count operations
        operations_count = 0
        if 'paths' in spec:
            for path, methods in spec['paths'].items():
                if isinstance(methods, dict):
                    for method, operation in methods.items():
                        if isinstance(operation, dict) and 'operationId' in operation:
                            operations_count += 1
        
        has_operations = operations_count > 0
        log_result(f"Has operations: {operations_count} operations", has_operations)
        if not has_operations:
            all_passed = False
        
        # Test security schemes
        components = spec.get('components', {})
        security_schemes = components.get('securitySchemes', {})
        has_security = len(security_schemes) > 0
        log_result(f"Has security schemes: {list(security_schemes.keys())}", has_security)
        if not has_security:
            all_passed = False
        
    except json.JSONDecodeError as e:
        log_result("OpenAPI spec JSON validity", False, f"JSON error: {e}")
        all_passed = False
    except FileNotFoundError:
        log_result("OpenAPI spec file exists", False, f"File not found: {spec_path}")
        all_passed = False
    
    return all_passed


def test_requirements():
    """Test requirements.txt."""
    print("\n=== Testing Requirements ===")
    
    requirements_path = Path(__file__).parent / "requirements.txt"
    all_passed = True
    
    try:
        with open(requirements_path, 'r') as f:
            content = f.read()
        
        # Required packages for FastMCP compliance
        required_packages = [
            'python-dotenv',
            'fastmcp',
            'httpx',
            'loguru',
            'pydantic'
        ]
        
        for package in required_packages:
            has_package = package in content
            log_result(f"Has required package: {package}", has_package)
            if not has_package:
                all_passed = False
        
        # Check for version constraints
        lines = [line.strip() for line in content.split('\n') if line.strip() and not line.startswith('#')]
        versioned_lines = [line for line in lines if '>=' in line or '==' in line]
        has_versions = len(versioned_lines) > 0
        log_result(f"Has version constraints: {len(versioned_lines)} packages", has_versions)
        
    except FileNotFoundError:
        log_result("Requirements file exists", False, f"File not found: {requirements_path}")
        all_passed = False
    
    return all_passed


def test_dockerfile():
    """Test Dockerfile."""
    print("\n=== Testing Dockerfile ===")
    
    dockerfile_path = Path(__file__).parent / "Dockerfile"
    all_passed = True
    
    try:
        with open(dockerfile_path, 'r') as f:
            content = f.read()
        
        # Required Dockerfile elements
        required_elements = [
            ('FROM python:', 'Base Python image'),
            ('WORKDIR', 'Working directory'),
            ('COPY requirements.txt', 'Requirements copy'),
            ('RUN pip install', 'Dependency installation'),
            ('EXPOSE', 'Port exposure'),
            ('CMD', 'Start command'),
            ('USER appuser', 'Non-root user'),
            ('HEALTHCHECK', 'Health check')
        ]
        
        for element, description in required_elements:
            has_element = element in content
            log_result(f"Has {description}", has_element)
            if not has_element:
                all_passed = False
        
    except FileNotFoundError:
        log_result("Dockerfile exists", False, f"File not found: {dockerfile_path}")
        all_passed = False
    
    return all_passed


def test_env_example():
    """Test .env.example file."""
    print("\n=== Testing Environment Configuration ===")
    
    env_path = Path(__file__).parent / ".env.example"
    all_passed = True
    
    try:
        with open(env_path, 'r') as f:
            content = f.read()
        
        # Required environment variables
        required_vars = [
            'MERAKI_API_KEY',
            'MERAKI_BASE_URL',
            'LOG_LEVEL'
        ]
        
        for var in required_vars:
            has_var = var in content
            log_result(f"Has environment variable: {var}", has_var)
            if not has_var:
                all_passed = False
        
        # Check for documentation
        has_comments = '#' in content
        log_result("Has documentation comments", has_comments)
        
    except FileNotFoundError:
        log_result(".env.example exists", False, f"File not found: {env_path}")
        all_passed = False
    
    return all_passed


def test_python_syntax():
    """Test Python files for syntax errors."""
    print("\n=== Testing Python Syntax ===")
    
    python_files = [
        '__init__.py',
        'meraki_mcp_server.py',
        'health_check.py',
        'validate_openapi.py'
    ]
    
    all_passed = True
    
    for file_name in python_files:
        file_path = Path(__file__).parent / file_name
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Try to compile the source
            compile(source, file_path, 'exec')
            log_result(f"Python syntax valid: {file_name}", True)
            
        except SyntaxError as e:
            log_result(f"Python syntax valid: {file_name}", False, f"Syntax error: {e}")
            all_passed = False
        except FileNotFoundError:
            log_result(f"Python file exists: {file_name}", False, f"File not found: {file_path}")
            all_passed = False
    
    return all_passed


def main():
    """Run all compliance tests."""
    print("🚀 Meraki MCP Server Compliance Validator")
    print("=" * 50)
    
    test_functions = [
        test_file_structure,
        test_openapi_spec,
        test_requirements,
        test_dockerfile,
        test_env_example,
        test_python_syntax
    ]
    
    total_passed = 0
    total_tests = len(test_functions)
    
    for test_func in test_functions:
        try:
            if test_func():
                total_passed += 1
            else:
                print(f"    Some checks in {test_func.__name__} failed")
        except Exception as e:
            print(f"❌ FAIL: {test_func.__name__} - Unexpected error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 COMPLIANCE SUMMARY")
    print(f"Passed: {total_passed}/{total_tests} test categories")
    
    if total_passed == total_tests:
        print("🎉 ALL COMPLIANCE TESTS PASSED!")
        print("✅ Implementation meets GoFastMCP OpenAPI standards")
        return True
    else:
        print(f"❌ {total_tests - total_passed} test categories have failures")
        print("⚠️  Please fix the issues above for full compliance")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)