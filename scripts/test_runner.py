#!/usr/bin/env python3
"""
Comprehensive test runner with coverage reporting and quality gates.
Provides unified interface for running all tests with quality metrics.
"""
import sys
import subprocess
import json
import time
from pathlib import Path
from typing import Dict, List, Any
import argparse


class TestRunner:
    """Comprehensive test runner with quality gates."""

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.results = {}
        self.start_time = time.time()

    def run_command(self, command: List[str], description: str) -> Dict[str, Any]:
        """Run a command and capture results."""
        print(f"\n{'='*60}")
        print(f"Running: {description}")
        print(f"Command: {' '.join(command)}")
        print(f"{'='*60}")

        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            duration = time.time() - start_time

            if result.stdout:
                print("STDOUT:")
                print(result.stdout)

            if result.stderr and result.returncode != 0:
                print("STDERR:")
                print(result.stderr)

            return {
                'command': ' '.join(command),
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': duration,
                'success': result.returncode == 0
            }

        except subprocess.TimeoutExpired:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'stdout': '',
                'stderr': 'Command timed out after 5 minutes',
                'duration': time.time() - start_time,
                'success': False
            }

        except Exception as e:
            return {
                'command': ' '.join(command),
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': time.time() - start_time,
                'success': False
            }

    def run_security_tests(self) -> bool:
        """Run security tests and checks."""
        print(f"\n{'#'*60}")
        print("SECURITY TESTING")
        print(f"{'#'*60}")

        # Run security-specific tests
        security_test_result = self.run_command([
            'python', '-m', 'pytest',
            'tests/security/',
            '-v',
            '--tb=short'
        ], "Security Tests")

        # Run bandit security scanner
        bandit_result = self.run_command([
            'bandit',
            '-r', 'src/',
            '--severity-level', 'medium',
            '-f', 'json',
            '-o', 'security-report.json'
        ], "Bandit Security Scan")

        # Run safety check for vulnerabilities
        safety_result = self.run_command([
            'safety', 'check', '--json'
        ], "Safety Vulnerability Check")

        self.results['security'] = {
            'tests': security_test_result,
            'bandit': bandit_result,
            'safety': safety_result,
            'overall_success': all([
                security_test_result['success'],
                bandit_result['success'],
                safety_result['success']
            ])
        }

        return self.results['security']['overall_success']

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage."""
        print(f"\n{'#'*60}")
        print("UNIT TESTING")
        print(f"{'#'*60}")

        unit_test_result = self.run_command([
            'python', '-m', 'pytest',
            'tests/unit/',
            '-v',
            '--cov=src',
            '--cov-report=xml',
            '--cov-report=html',
            '--cov-report=term',
            '--cov-fail-under=80'
        ], "Unit Tests with Coverage")

        self.results['unit_tests'] = unit_test_result
        return unit_test_result['success']

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        print(f"\n{'#'*60}")
        print("INTEGRATION TESTING")
        print(f"{'#'*60}")

        integration_test_result = self.run_command([
            'python', '-m', 'pytest',
            'tests/integration/',
            '-v',
            '--tb=short'
        ], "Integration Tests")

        self.results['integration_tests'] = integration_test_result
        return integration_test_result['success']

    def run_api_tests(self) -> bool:
        """Run API tests."""
        print(f"\n{'#'*60}")
        print("API TESTING")
        print(f"{'#'*60}")

        api_test_result = self.run_command([
            'python', '-m', 'pytest',
            'tests/api/',
            '-v',
            '--tb=short'
        ], "API Endpoint Tests")

        self.results['api_tests'] = api_test_result
        return api_test_result['success']

    def run_performance_tests(self) -> bool:
        """Run performance tests."""
        print(f"\n{'#'*60}")
        print("PERFORMANCE TESTING")
        print(f"{'#'*60}")

        performance_test_result = self.run_command([
            'python', '-m', 'pytest',
            'tests/performance/',
            '-v',
            '--tb=short'
        ], "Performance Tests")

        self.results['performance_tests'] = performance_test_result
        return performance_test_result['success']

    def run_code_quality_checks(self) -> bool:
        """Run code quality and linting checks."""
        print(f"\n{'#'*60}")
        print("CODE QUALITY CHECKS")
        print(f"{'#'*60}")

        # Run flake8
        flake8_result = self.run_command([
            'flake8',
            'src/', 'tests/',
            '--max-line-length=120',
            '--extend-ignore=E203,W503'
        ], "Flake8 Linting")

        # Run black format checking
        black_result = self.run_command([
            'black',
            '--check',
            '--diff',
            'src/', 'tests/'
        ], "Black Format Check")

        # Run isort import sorting check
        isort_result = self.run_command([
            'isort',
            '--check-only',
            '--diff',
            'src/', 'tests/'
        ], "Import Sorting Check")

        # Run mypy type checking
        mypy_result = self.run_command([
            'mypy',
            'src/',
            '--ignore-missing-imports'
        ], "MyPy Type Checking")

        self.results['code_quality'] = {
            'flake8': flake8_result,
            'black': black_result,
            'isort': isort_result,
            'mypy': mypy_result,
            'overall_success': all([
                flake8_result['success'],
                black_result['success'],
                isort_result['success'],
                mypy_result['success']
            ])
        }

        return self.results['code_quality']['overall_success']

    def parse_coverage_report(self) -> Dict[str, Any]:
        """Parse coverage report and extract metrics."""
        coverage_xml = self.project_root / 'coverage.xml'
        if not coverage_xml.exists():
            return {'error': 'Coverage report not found'}

        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(coverage_xml)
            root = tree.getroot()

            # Extract overall coverage
            coverage_elem = root.find('.//coverage')
            if coverage_elem is not None:
                line_rate = float(coverage_elem.get('line-rate', 0)) * 100
                branch_rate = float(coverage_elem.get('branch-rate', 0)) * 100

                return {
                    'line_coverage': round(line_rate, 2),
                    'branch_coverage': round(branch_rate, 2),
                    'lines_covered': int(coverage_elem.get('lines-covered', 0)),
                    'lines_valid': int(coverage_elem.get('lines-valid', 0))
                }

        except Exception as e:
            return {'error': f'Failed to parse coverage: {str(e)}'}

        return {'error': 'Could not extract coverage data'}

    def generate_quality_report(self) -> Dict[str, Any]:
        """Generate comprehensive quality report."""
        total_duration = time.time() - self.start_time
        coverage_metrics = self.parse_coverage_report()

        # Calculate overall success
        test_categories = ['security', 'unit_tests', 'integration_tests', 'api_tests', 'performance_tests']
        test_success = all(
            self.results.get(category, {}).get('overall_success' if category == 'security' else 'success', False)
            for category in test_categories
        )

        code_quality_success = self.results.get('code_quality', {}).get('overall_success', False)
        overall_success = test_success and code_quality_success

        report = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
            'total_duration': round(total_duration, 2),
            'overall_success': overall_success,
            'coverage': coverage_metrics,
            'test_results': {
                'security': self.results.get('security', {}).get('overall_success', False),
                'unit_tests': self.results.get('unit_tests', {}).get('success', False),
                'integration_tests': self.results.get('integration_tests', {}).get('success', False),
                'api_tests': self.results.get('api_tests', {}).get('success', False),
                'performance_tests': self.results.get('performance_tests', {}).get('success', False)
            },
            'code_quality': {
                'overall': self.results.get('code_quality', {}).get('overall_success', False),
                'flake8': self.results.get('code_quality', {}).get('flake8', {}).get('success', False),
                'black': self.results.get('code_quality', {}).get('black', {}).get('success', False),
                'isort': self.results.get('code_quality', {}).get('isort', {}).get('success', False),
                'mypy': self.results.get('code_quality', {}).get('mypy', {}).get('success', False)
            },
            'quality_gates': {
                'min_coverage': coverage_metrics.get('line_coverage', 0) >= 80,
                'all_tests_pass': test_success,
                'code_quality_pass': code_quality_success,
                'security_pass': self.results.get('security', {}).get('overall_success', False)
            }
        }

        return report

    def save_reports(self, report: Dict[str, Any]) -> None:
        """Save test reports to files."""
        # Save main quality report
        with open('quality-report.json', 'w') as f:
            json.dump(report, f, indent=2)

        # Save detailed results
        with open('test-results-detailed.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        print(f"\nReports saved:")
        print(f"  - quality-report.json")
        print(f"  - test-results-detailed.json")
        if Path('coverage.xml').exists():
            print(f"  - coverage.xml")
        if Path('htmlcov').exists():
            print(f"  - htmlcov/ (HTML coverage report)")

    def print_summary(self, report: Dict[str, Any]) -> None:
        """Print test summary."""
        print(f"\n{'='*80}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*80}")

        print(f"Total Duration: {report['total_duration']:.2f}s")
        print(f"Overall Success: {'✅ PASS' if report['overall_success'] else '❌ FAIL'}")

        print(f"\nCoverage:")
        coverage = report['coverage']
        if 'error' not in coverage:
            print(f"  Line Coverage: {coverage['line_coverage']:.1f}%")
            print(f"  Branch Coverage: {coverage['branch_coverage']:.1f}%")
            print(f"  Lines: {coverage['lines_covered']}/{coverage['lines_valid']}")
        else:
            print(f"  Error: {coverage['error']}")

        print(f"\nTest Results:")
        for category, success in report['test_results'].items():
            status = '✅ PASS' if success else '❌ FAIL'
            print(f"  {category.replace('_', ' ').title()}: {status}")

        print(f"\nCode Quality:")
        for check, success in report['code_quality'].items():
            if check != 'overall':
                status = '✅ PASS' if success else '❌ FAIL'
                print(f"  {check.upper()}: {status}")

        print(f"\nQuality Gates:")
        for gate, passed in report['quality_gates'].items():
            status = '✅ PASS' if passed else '❌ FAIL'
            gate_name = gate.replace('_', ' ').title()
            print(f"  {gate_name}: {status}")

        if not report['overall_success']:
            print(f"\n❌ QUALITY GATES FAILED")
            sys.exit(1)
        else:
            print(f"\n✅ ALL QUALITY GATES PASSED")

    def run_full_test_suite(self, skip_performance: bool = False) -> bool:
        """Run complete test suite with all quality checks."""
        print(f"{'='*80}")
        print("COMPREHENSIVE TEST SUITE EXECUTION")
        print(f"{'='*80}")
        print(f"Project Root: {self.project_root}")
        print(f"Start Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime(self.start_time))}")

        # Run all test categories
        success = True

        # Security tests
        if not self.run_security_tests():
            success = False

        # Unit tests with coverage
        if not self.run_unit_tests():
            success = False

        # Integration tests
        if not self.run_integration_tests():
            success = False

        # API tests
        if not self.run_api_tests():
            success = False

        # Performance tests (optional)
        if not skip_performance:
            if not self.run_performance_tests():
                success = False

        # Code quality checks
        if not self.run_code_quality_checks():
            success = False

        # Generate and save reports
        report = self.generate_quality_report()
        self.save_reports(report)
        self.print_summary(report)

        return success


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description='Comprehensive test runner with quality gates')
    parser.add_argument('--skip-performance', action='store_true',
                      help='Skip performance tests (useful for quick checks)')
    parser.add_argument('--project-root', type=Path,
                      help='Project root directory (default: current directory)')

    args = parser.parse_args()

    runner = TestRunner(args.project_root)
    success = runner.run_full_test_suite(skip_performance=args.skip_performance)

    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()