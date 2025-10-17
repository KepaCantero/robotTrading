"""
Project Conductor Demo

Demonstrates the Project Conductor orchestrating the complete development lifecycle
by coordinating existing agent systems (Code Review, Testing, etc.).
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent))

from project_conductor import ProjectConductor, implement_task


async def demo_project_conductor():
    """Demonstrate the Project Conductor system."""
    
    print("🎭 AlgoTrading Project Conductor Demo")
    print("=" * 50)
    
    # Initialize conductor
    project_path = Path(__file__).parent.parent
    conductor = ProjectConductor(
        project_path=str(project_path),
        memory_bank_path=".memory"
    )
    
    print(f"📁 Project Path: {project_path}")
    print(f"🧠 Memory Bank: .memory")
    print()
    
    # Demo 1: Implement T001 (already implemented)
    print("🔍 Demo 1: Implementing T001 (FastAPI Base Structure)")
    print("-" * 30)
    
    try:
        report = await conductor.implement_task("T001")
        
        print(f"✅ Task implementation completed!")
        print(f"📊 Overall Status: {'✅ SUCCESS' if report['execution_summary']['overall_status'] else '❌ FAILED'}")
        print(f"⏱️ Execution Time: {report['execution_summary']['start_time']} - {report['execution_summary']['end_time']}")
        print(f"🔄 Total Phases: {report['execution_summary']['total_phases']}")
        print()
        
        # Show quality metrics
        quality_metrics = report['quality_metrics']
        print("📈 Quality Metrics:")
        print(f"   Code Quality: {'✅' if quality_metrics['code_quality'] else '❌'}")
        print(f"   Test Quality: {'✅' if quality_metrics['test_quality'] else '❌'}")
        print(f"   Coverage Quality: {'✅' if quality_metrics['coverage_quality'] else '❌'}")
        print()
        
        # Show next steps
        print("🚀 Next Steps:")
        for step in report['next_steps']:
            print(f"   {step}")
        print()
        
    except Exception as e:
        print(f"❌ Error implementing T001: {str(e)}")
        print()
    
    # Demo 2: Show execution status
    print("📊 Demo 2: Execution Status")
    print("-" * 30)
    
    status = conductor.get_execution_status()
    print(f"Current Task: {status['current_task']}")
    print(f"Current Phase: {status['current_phase']}")
    print(f"Execution Log Entries: {len(status['execution_log'])}")
    print()
    
    print("Available Systems:")
    for system, available in status['systems_available'].items():
        print(f"   {system}: {'✅' if available else '❌'}")
    print()
    
    # Demo 3: Show phase breakdown
    print("🔄 Demo 3: Phase Breakdown")
    print("-" * 30)
    
    if status['execution_log']:
        for i, log_entry in enumerate(status['execution_log'], 1):
            print(f"{i}. {log_entry['phase']} - {log_entry['status']}")
    else:
        print("No execution log available")
    print()
    
    # Demo 4: Show orchestrator specifications
    print("📋 Demo 4: Orchestrator Specifications")
    print("-" * 30)
    
    if conductor.orchestrator_spec:
        spec = conductor.orchestrator_spec.get('multi_agent_orchestrator', {})
        agent_roles = spec.get('agent_roles', {})
        
        print(f"Defined Agent Roles: {len(agent_roles)}")
        for role_name, role_info in agent_roles.items():
            print(f"   {role_info.get('role', role_name)}: {role_info.get('responsibility', 'N/A')}")
        print()
        
        execution_flow = spec.get('execution_flow', {})
        print(f"Execution Flow Steps: {len(execution_flow)}")
        for step_name, step_info in execution_flow.items():
            print(f"   {step_name}: {step_info.get('agent', 'N/A')}")
        print()
    else:
        print("No orchestrator specifications loaded")
        print()
    
    print("🎉 Demo completed successfully!")
    print("=" * 50)


async def demo_convenience_function():
    """Demonstrate the convenience function."""
    
    print("🚀 Convenience Function Demo")
    print("=" * 50)
    
    project_path = Path(__file__).parent.parent
    
    try:
        # Use the convenience function
        report = await implement_task(str(project_path), "T001")
        
        print(f"✅ Convenience function executed successfully!")
        print(f"📊 Task ID: {report['task_id']}")
        print(f"🎯 Overall Status: {'✅ SUCCESS' if report['execution_summary']['overall_status'] else '❌ FAILED'}")
        print()
        
        # Show phase results summary
        phase_results = report['phase_results']
        print("📋 Phase Results Summary:")
        for phase_name, phase_result in phase_results.items():
            if isinstance(phase_result, dict):
                status = "✅" if phase_result.get('status') == 'completed' else "🔄"
                print(f"   {phase_name}: {status}")
        print()
        
    except Exception as e:
        print(f"❌ Error with convenience function: {str(e)}")
        print()
    
    print("🎉 Convenience function demo completed!")


async def demo_system_integration():
    """Demonstrate integration with existing agent systems."""
    
    print("🔗 System Integration Demo")
    print("=" * 50)
    
    project_path = Path(__file__).parent.parent
    conductor = ProjectConductor(str(project_path), ".memory")
    
    # Test Code Review System integration
    print("🔍 Testing Code Review System Integration")
    print("-" * 30)
    
    try:
        code_review_status = conductor.code_review_system.get_agent_status()
        print(f"Code Review Agents: {len(code_review_status)}")
        for agent_name, status in code_review_status.items():
            print(f"   {status['name']}: {status['findings_count']} findings")
        print()
    except Exception as e:
        print(f"❌ Code Review System error: {str(e)}")
        print()
    
    # Test Testing System integration
    print("🧪 Testing Testing System Integration")
    print("-" * 30)
    
    try:
        testing_status = conductor.testing_system.get_agent_status()
        print(f"Testing Agents: {len(testing_status)}")
        for agent_name, status in testing_status.items():
            print(f"   {status['name']}: {status['results_count']} results")
        print()
    except Exception as e:
        print(f"❌ Testing System error: {str(e)}")
        print()
    
    print("🎉 System integration demo completed!")


if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Full Project Conductor demo")
    print("2. Convenience function demo")
    print("3. System integration demo")
    
    choice = input("Enter choice (1, 2, or 3): ").strip()
    
    if choice == "1":
        asyncio.run(demo_project_conductor())
    elif choice == "2":
        asyncio.run(demo_convenience_function())
    elif choice == "3":
        asyncio.run(demo_system_integration())
    else:
        print("Invalid choice. Running full demo...")
        asyncio.run(demo_project_conductor())
