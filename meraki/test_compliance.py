#!/usr/bin/env python3
"""
Test suite for Meraki MCP Server.
Validates the complete implementation against GoFastMCP standards.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from loguru import logger


class MerakiMCPTester:
    """Comprehensive test suite for Meraki MCP Server."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.test_results: List[Dict[str, Any]] = []
        
    def log_test_result(self, test_name: str, passed: bool, message: str = ""):
        """Log test result."""
        if passed:
            self.tests_passed += 1
            logger.success(f"✅ {test_name}")
        else:
            self.tests_failed += 1
            logger.error(f"❌ {test_name}: {message}")
        
        self.test_results.append({
            'name': test_name,
            'passed': passed,
            'message': message
        })
    
    def test_file_structure(self) -> None:
        """Test that all required files are present."""
        required_files = [
            '__init__.py',
            'meraki_mcp_server.py',
            'health_check.py',
            'validate_openapi.py',
            'requirements.txt',
            'Dockerfile',
            '.env.example',
            'openapi/spec3.json'
        ]
        
        for file_path in required_files:
            full_path = Path(__file__).parent / file_path
            exists = full_path.exists()
            self.log_test_result(
                f"File exists: {file_path}",
                exists,
                f"Missing file: {full_path}" if not exists else ""
            )
    
    def test_python_imports(self) -> None:
        """Test that all Python modules can be imported."""
        modules_to_test = [
            ('meraki_mcp_server', 'MerakiMCPServer'),
            ('health_check', 'HealthCheck'),
            ('validate_openapi', 'OpenAPIValidator')
        ]
        
        for module_name, class_name in modules_to_test:
            try:
                module = __import__(module_name)
                if hasattr(module, class_name):
                    self.log_test_result(
                        f"Import {module_name}.{class_name}",
                        True
                    )
                else:
                    self.log_test_result(
                        f"Import {module_name}.{class_name}",
                        False,
                        f"Class {class_name} not found in module"
                    )
            except ImportError as e:
                self.log_test_result(
                    f"Import {module_name}",
                    False,
                    f"Import error: {e}"
                )
    
    def test_openapi_spec_validity(self) -> None:
        """Test OpenAPI specification validity."""
        spec_path = Path(__file__).parent / "openapi" / "spec3.json"
        
        try:
            with open(spec_path, 'r', encoding='utf-8') as f:
                spec = json.load(f)
            
            # Test basic structure
            required_fields = ['openapi', 'info', 'paths']
            for field in required_fields:
                exists = field in spec
                self.log_test_result(
                    f"OpenAPI spec has {field}",
                    exists,
                    f"Missing required field: {field}" if not exists else ""
                )
            
            # Test version
            if 'openapi' in spec:
                version_valid = spec['openapi'].startswith('3.')
                self.log_test_result(
                    "OpenAPI version is 3.x",
                    version_valid,
                    f"Invalid version: {spec['openapi']}" if not version_valid else ""
                )
            
            # Test paths count
            if 'paths' in spec:
                paths_count = len(spec['paths'])
                has_paths = paths_count > 0
                self.log_test_result(
                    f"OpenAPI spec has paths ({paths_count})",
                    has_paths,
                    "No paths defined" if not has_paths else ""
                )
            
            # Test operations count
            operations_count = 0
            if 'paths' in spec:
                for path, methods in spec['paths'].items():
                    if isinstance(methods, dict):
                        for method, operation in methods.items():
                            if isinstance(operation, dict) and 'operationId' in operation:
                                operations_count += 1
            
            has_operations = operations_count > 0
            self.log_test_result(
                f"OpenAPI spec has operations ({operations_count})",
                has_operations,
                "No operations defined" if not has_operations else ""
            )
            
        except json.JSONDecodeError as e:
            self.log_test_result(
                "OpenAPI spec JSON validity",
                False,
                f"JSON decode error: {e}"
            )
        except FileNotFoundError:
            self.log_test_result(
                "OpenAPI spec file exists",
                False,
                f"File not found: {spec_path}"
            )
    
    def test_configuration_model(self) -> None:
        """Test configuration model validation."""
        try:
            from meraki_mcp_server import MerakiMCPConfig
            
            # Test valid configuration
            try:
                config = MerakiMCPConfig(api_key="test_key")
                self.log_test_result(
                    "Configuration model accepts valid data",
                    True
                )
            except Exception as e:
                self.log_test_result(
                    "Configuration model accepts valid data",
                    False,
                    f"Validation error: {e}"
                )
            
            # Test missing required field
            try:
                config = MerakiMCPConfig()
                self.log_test_result(
                    "Configuration model rejects missing required fields",
                    False,
                    "Should have raised validation error"
                )
            except Exception:
                self.log_test_result(
                    "Configuration model rejects missing required fields",
                    True
                )
            
        except ImportError as e:
            self.log_test_result(
                "Configuration model import",
                False,
                f"Import error: {e}"
            )
    
    def test_health_check_functionality(self) -> None:
        """Test health check functionality."""
        try:
            from health_check import HealthCheck
            
            # Test health check instantiation
            health = HealthCheck("test_api_key")
            self.log_test_result(
                "Health check instantiation",
                True
            )
            
            # Test OpenAPI spec check
            spec_check = health.check_openapi_spec()
            spec_valid = spec_check.get('status') == 'healthy'
            self.log_test_result(
                "Health check - OpenAPI spec validation",
                spec_valid,
                spec_check.get('error', '') if not spec_valid else ""
            )
            
        except ImportError as e:
            self.log_test_result(
                "Health check import",
                False,
                f"Import error: {e}"
            )
        except Exception as e:
            self.log_test_result(
                "Health check functionality",
                False,
                f"Error: {e}"
            )
    
    def test_dockerfile_validity(self) -> None:
        """Test Dockerfile for common issues."""
        dockerfile_path = Path(__file__).parent / "Dockerfile"
        
        try:
            with open(dockerfile_path, 'r') as f:
                dockerfile_content = f.read()
            
            # Test for required sections
            required_sections = [
                'FROM',
                'WORKDIR',
                'COPY requirements.txt',
                'RUN pip install',
                'EXPOSE',
                'CMD'
            ]
            
            for section in required_sections:
                has_section = section in dockerfile_content
                self.log_test_result(
                    f"Dockerfile has {section}",
                    has_section,
                    f"Missing: {section}" if not has_section else ""
                )
            
            # Test for health check
            has_healthcheck = 'HEALTHCHECK' in dockerfile_content
            self.log_test_result(
                "Dockerfile has HEALTHCHECK",
                has_healthcheck,
                "Missing HEALTHCHECK directive" if not has_healthcheck else ""
            )
            
            # Test for non-root user
            has_user = 'USER appuser' in dockerfile_content
            self.log_test_result(
                "Dockerfile uses non-root user",
                has_user,
                "Missing USER directive" if not has_user else ""
            )
            
        except FileNotFoundError:
            self.log_test_result(
                "Dockerfile exists",
                False,
                f"File not found: {dockerfile_path}"
            )
    
    def test_requirements_validity(self) -> None:
        """Test requirements.txt for validity."""
        requirements_path = Path(__file__).parent / "requirements.txt"
        
        try:
            with open(requirements_path, 'r') as f:
                requirements = f.read().strip().split('\n')
            
            # Filter out comments and empty lines
            packages = [
                line.strip() for line in requirements 
                if line.strip() and not line.strip().startswith('#')
            ]
            
            # Test for required packages
            required_packages = [
                'python-dotenv',
                'fastmcp',
                'httpx',
                'loguru',
                'pydantic'
            ]
            
            for package in required_packages:
                has_package = any(package in req for req in packages)
                self.log_test_result(
                    f"Requirements has {package}",
                    has_package,
                    f"Missing package: {package}" if not has_package else ""
                )
            
            # Test for version constraints
            versioned_packages = [req for req in packages if '>=' in req or '==' in req]
            has_versions = len(versioned_packages) > 0
            self.log_test_result(
                "Requirements has version constraints",
                has_versions,
                "No version constraints found" if not has_versions else ""
            )
            
        except FileNotFoundError:
            self.log_test_result(
                "Requirements file exists",
                False,
                f"File not found: {requirements_path}"
            )
    
    def test_env_example_completeness(self) -> None:
        """Test .env.example file completeness."""
        env_example_path = Path(__file__).parent / ".env.example"
        
        try:
            with open(env_example_path, 'r') as f:
                env_content = f.read()
            
            # Test for required environment variables
            required_vars = [
                'MERAKI_API_KEY',
                'MERAKI_BASE_URL',
                'LOG_LEVEL'
            ]
            
            for var in required_vars:
                has_var = var in env_content
                self.log_test_result(
                    f".env.example has {var}",
                    has_var,
                    f"Missing variable: {var}" if not has_var else ""
                )
            
            # Test for comments/documentation
            has_comments = '#' in env_content
            self.log_test_result(
                ".env.example has documentation",
                has_comments,
                "No comments found" if not has_comments else ""
            )
            
        except FileNotFoundError:
            self.log_test_result(
                ".env.example exists",
                False,
                f"File not found: {env_example_path}"
            )
    
    async def run_all_tests(self) -> bool:
        """Run all tests and return overall success."""
        logger.info("Starting comprehensive test suite...")
        
        # Run all test methods
        test_methods = [
            self.test_file_structure,
            self.test_python_imports,
            self.test_openapi_spec_validity,
            self.test_configuration_model,
            self.test_health_check_functionality,
            self.test_dockerfile_validity,
            self.test_requirements_validity,
            self.test_env_example_completeness
        ]
        
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                logger.error(f"Test method {test_method.__name__} failed: {e}")
                self.tests_failed += 1
        
        # Print summary
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        logger.info(f"\nTest Summary:")
        logger.info(f"Total tests: {total_tests}")
        logger.info(f"Passed: {self.tests_passed}")
        logger.info(f"Failed: {self.tests_failed}")
        logger.info(f"Success rate: {success_rate:.1f}%")
        
        if self.tests_failed == 0:
            logger.success("🎉 All tests passed! Implementation is compliant.")
            return True
        else:
            logger.error(f"❌ {self.tests_failed} tests failed. Please fix the issues.")
            return False
    
    def get_detailed_report(self) -> Dict[str, Any]:
        """Get detailed test report."""
        return {
            'summary': {
                'total': self.tests_passed + self.tests_failed,
                'passed': self.tests_passed,
                'failed': self.tests_failed,
                'success_rate': (self.tests_passed / (self.tests_passed + self.tests_failed) * 100) if (self.tests_passed + self.tests_failed) > 0 else 0
            },
            'results': self.test_results
        }


async def main():
    """Main test entry point."""
    # Configure logging
    logger.remove()
    logger.add(sys.stderr, format="<level>{level}</level> | {message}")
    
    tester = MerakiMCPTester()
    success = await tester.run_all_tests()
    
    # Save detailed report
    report = tester.get_detailed_report()
    report_path = Path(__file__).parent / "test_report.json"
    
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    logger.info(f"Detailed report saved to: {report_path}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())