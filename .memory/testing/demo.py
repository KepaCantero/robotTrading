"""
Testing System Demo

Demonstrates the testing system with specialized agents
executing tests, diagnosing failures, and applying fixes.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .orchestrator import TestingOrchestrator


async def demo_testing_system():
    """Demonstrate the testing system."""
    
    print("🧪 AlgoTrading Testing System Demo")
    print("=" * 50)
    
    # Initialize orchestrator
    project_path = Path(__file__).parent.parent.parent
    orchestrator = TestingOrchestrator(
        project_path=str(project_path),
        memory_bank_path=".memory"
    )
    
    print(f"📁 Project Path: {project_path}")
    print(f"🧠 Memory Bank: .memory")
    print()
    
    # Demo 1: Run all tests
    print("🔍 Demo 1: Running All Tests")
    print("-" * 30)
    
    try:
        report = await orchestrator.test_all()
        
        print(f"✅ Test execution completed!")
        print(f"📊 Total Results: {report['metadata']['total_results']}")
        print(f"✅ Passed: {report['metadata']['passed_tests']}")
        print(f"❌ Failed: {report['metadata']['failed_tests']}")
        print(f"🔴 Errors: {report['metadata']['error_tests']}")
        print(f"⏭️ Skipped: {report['metadata']['skipped_tests']}")
        print()
        
        # Show executive summary
        if 'executive_summary' in report:
            summary = report['executive_summary']
            print("📋 Executive Summary:")
            print(f"   Status: {summary.get('status', 'Unknown')}")
            print(f"   Success Rate: {summary.get('success_rate', 0):.1f}%")
            print(f"   Key Insights: {len(summary.get('key_insights', []))} insights")
            print()
        
        # Show recommendations
        if 'recommendations' in report and report['recommendations']:
            print("💡 Top Recommendations:")
            for i, rec in enumerate(report['recommendations'][:3], 1):
                print(f"   {i}. {rec['priority'].upper()} - {rec['recommendation']}")
            print()
        
    except Exception as e:
        print(f"❌ Error running tests: {str(e)}")
        print()
    
    # Demo 2: Run unit tests only
    print("🔍 Demo 2: Running Unit Tests Only")
    print("-" * 30)
    
    try:
        report = await orchestrator.test_unit()
        
        print(f"✅ Unit test execution completed!")
        print(f"📊 Total Results: {report['metadata']['total_results']}")
        print(f"✅ Passed: {report['metadata']['passed_tests']}")
        print(f"❌ Failed: {report['metadata']['failed_tests']}")
        print()
        
    except Exception as e:
        print(f"❌ Error running unit tests: {str(e)}")
        print()
    
    # Demo 3: Run tests with automatic fixing
    print("🔍 Demo 3: Running Tests with Auto-Fixing")
    print("-" * 30)
    
    try:
        report = await orchestrator.test_with_fixes("unit")
        
        print(f"✅ Test execution with fixes completed!")
        print(f"📊 Total Results: {report['metadata']['total_results']}")
        print(f"✅ Passed: {report['metadata']['passed_tests']}")
        print(f"❌ Failed: {report['metadata']['failed_tests']}")
        print()
        
        # Show fix information
        if 'fix_summary' in report and report['fix_summary']:
            fix_summary = report['fix_summary']
            print("🔧 Fixes Applied:")
            print(f"   Fixes Applied: {fix_summary.get('fixes_applied', 0)}")
            print(f"   Fix Branch: {fix_summary.get('fix_branch', 'N/A')}")
            print()
        
    except Exception as e:
        print(f"❌ Error running tests with fixes: {str(e)}")
        print()
    
    # Demo 4: Show agent status
    print("🤖 Agent Status")
    print("-" * 30)
    
    agent_status = orchestrator.get_agent_status()
    for agent_name, status in agent_status.items():
        print(f"   {status['name']}: {status['results_count']} results, "
              f"{status['success_rate']:.1f}% success rate")
    print()
    
    # Demo 5: Generate test summary
    print("📄 Generating Test Summary")
    print("-" * 30)
    
    try:
        summary_report = await orchestrator.generate_test_summary()
        print("✅ Test summary generated successfully!")
        print("📝 Summary preview:")
        print(summary_report[:500] + "..." if len(summary_report) > 500 else summary_report)
        print()
        
    except Exception as e:
        print(f"❌ Error generating test summary: {str(e)}")
        print()
    
    # Demo 6: Export test results
    print("📤 Exporting Test Results")
    print("-" * 30)
    
    try:
        json_export = await orchestrator.export_test_results("json")
        print("✅ JSON export completed!")
        print(f"📊 Export size: {len(json_export)} characters")
        print()
        
    except Exception as e:
        print(f"❌ Error exporting test results: {str(e)}")
        print()
    
    # Final status
    print("🎯 Final Status")
    print("-" * 30)
    
    stability = orchestrator.get_system_stability()
    should_continue = orchestrator.should_continue_testing()
    
    print(f"🚦 System Stability: {stability}")
    print(f"🔄 Should Continue Testing: {'✅ YES' if should_continue else '❌ NO'}")
    print()
    
    print("🎉 Demo completed successfully!")
    print("=" * 50)


async def demo_specific_agent():
    """Demonstrate a specific agent's capabilities."""
    
    print("🤖 Specific Agent Demo: Test Executor")
    print("=" * 50)
    
    from .agents.test_executor import TestExecutor
    from .agents.base_test_agent import TestContext
    
    # Create test context
    context = TestContext(
        project_path="/demo",
        memory_bank_path=".memory",
        test_scope="unit",
        environment="local"
    )
    
    # Initialize agent
    agent = TestExecutor()
    
    # Execute tests
    results = await agent.execute(context)
    
    print(f"📊 Results: {len(results)}")
    print()
    
    for result in results:
        print(f"🔍 {result.status.value} - {result.test_name}")
        print(f"   Duration: {result.duration:.2f}s")
        print(f"   Output: {result.output[:100]}...")
        print()
    
    print("✅ Test Executor demo completed!")


async def demo_failure_diagnosis():
    """Demonstrate failure diagnosis capabilities."""
    
    print("🧠 Failure Diagnosis Demo")
    print("=" * 50)
    
    from .agents.failure_diagnostician import FailureDiagnostician
    from .agents.base_test_agent import TestContext, TestResult, TestStatus
    
    # Create test context
    context = TestContext(
        project_path="/demo",
        memory_bank_path=".memory",
        test_scope="unit",
        environment="local"
    )
    
    # Initialize agent
    agent = FailureDiagnostician()
    
    # Simulate some failed tests
    failed_tests = [
        TestResult(
            test_name="test_calculate_risk_ratio",
            status=TestStatus.FAILED,
            duration=0.5,
            output="TypeError: unsupported operand type(s) for /: 'str' and 'int'",
            error_message="TypeError: unsupported operand type(s) for /: 'str' and 'int'"
        ),
        TestResult(
            test_name="test_user_authentication",
            status=TestStatus.FAILED,
            duration=1.2,
            output="AssertionError: Expected True but got False",
            error_message="AssertionError: Expected True but got False"
        )
    ]
    
    # Analyze failures
    for test_result in failed_tests:
        await agent._diagnose_test_failure(test_result, context)
    
    print(f"📊 Diagnosed Failures: {len(agent.failures)}")
    print()
    
    for failure in agent.failures:
        print(f"🔍 {failure.test_name}")
        print(f"   Error Type: {failure.error_type}")
        print(f"   Root Cause: {failure.root_cause}")
        print(f"   Suggested Fix: {failure.suggested_fix}")
        print(f"   Confidence: {failure.confidence.value}")
        print()
    
    print("✅ Failure Diagnosis demo completed!")


if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Full system demo")
    print("2. Specific agent demo (Test Executor)")
    print("3. Failure diagnosis demo")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        asyncio.run(demo_testing_system())
    elif choice == "2":
        asyncio.run(demo_specific_agent())
    elif choice == "3":
        asyncio.run(demo_failure_diagnosis())
    else:
        print("Invalid choice. Running full system demo...")
        asyncio.run(demo_testing_system())
