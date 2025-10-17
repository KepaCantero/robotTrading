"""
Code Review System Demo

Demonstrates the code review system with specialized agents
analyzing code and generating comprehensive reports.
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent))

from .orchestrator import CodeReviewOrchestrator


async def demo_code_review():
    """Demonstrate the code review system."""
    
    print("🚀 AlgoTrading Code Review System Demo")
    print("=" * 50)
    
    # Initialize orchestrator
    project_path = Path(__file__).parent.parent.parent
    orchestrator = CodeReviewOrchestrator(
        project_path=str(project_path),
        memory_bank_path=".memory"
    )
    
    print(f"📁 Project Path: {project_path}")
    print(f"🧠 Memory Bank: .memory")
    print()
    
    # Demo 1: Review the main.py file
    print("🔍 Demo 1: Reviewing app/main.py")
    print("-" * 30)
    
    try:
        report = await orchestrator.review_file("app/main.py")
        
        print(f"✅ Review completed!")
        print(f"📊 Total Findings: {report['metadata']['total_findings']}")
        print(f"🔴 Critical: {report['metadata']['critical_findings']}")
        print(f"🟠 High: {report['metadata']['high_findings']}")
        print(f"🟡 Medium: {report['metadata']['medium_findings']}")
        print(f"🟢 Low: {report['metadata']['low_findings']}")
        print()
        
        # Show executive summary
        if 'executive_summary' in report:
            summary = report['executive_summary']
            print("📋 Executive Summary:")
            print(f"   Status: {summary.get('status', 'Unknown')}")
            print(f"   Key Insights: {len(summary.get('key_insights', []))} insights")
            print()
        
        # Show top recommendations
        if 'recommendations' in report and report['recommendations']:
            print("💡 Top Recommendations:")
            for i, rec in enumerate(report['recommendations'][:3], 1):
                print(f"   {i}. {rec['severity']} - {rec['recommendation'][:80]}...")
            print()
        
    except Exception as e:
        print(f"❌ Error reviewing app/main.py: {str(e)}")
        print()
    
    # Demo 2: Review test file
    print("🔍 Demo 2: Reviewing tests/test_main.py")
    print("-" * 30)
    
    try:
        report = await orchestrator.review_file("tests/test_main.py")
        
        print(f"✅ Review completed!")
        print(f"📊 Total Findings: {report['metadata']['total_findings']}")
        print(f"🔴 Critical: {report['metadata']['critical_findings']}")
        print(f"🟠 High: {report['metadata']['high_findings']}")
        print(f"🟡 Medium: {report['metadata']['medium_findings']}")
        print(f"🟢 Low: {report['metadata']['low_findings']}")
        print()
        
    except Exception as e:
        print(f"❌ Error reviewing tests/test_main.py: {str(e)}")
        print()
    
    # Demo 3: Show agent status
    print("🤖 Agent Status")
    print("-" * 30)
    
    agent_status = orchestrator.get_agent_status()
    for agent_name, status in agent_status.items():
        print(f"   {status['name']}: {status['findings_count']} findings, "
              f"{'🔴 Critical' if status['has_critical'] else '✅ Clean'}")
    print()
    
    # Demo 4: Generate summary report
    print("📄 Generating Summary Report")
    print("-" * 30)
    
    try:
        summary_report = await orchestrator.generate_summary_report()
        print("✅ Summary report generated successfully!")
        print("📝 Report preview:")
        print(summary_report[:500] + "..." if len(summary_report) > 500 else summary_report)
        print()
        
    except Exception as e:
        print(f"❌ Error generating summary report: {str(e)}")
        print()
    
    # Demo 5: Export findings
    print("📤 Exporting Findings")
    print("-" * 30)
    
    try:
        json_export = await orchestrator.export_findings("json")
        print("✅ JSON export completed!")
        print(f"📊 Export size: {len(json_export)} characters")
        print()
        
    except Exception as e:
        print(f"❌ Error exporting findings: {str(e)}")
        print()
    
    # Final status
    print("🎯 Final Status")
    print("-" * 30)
    
    should_block = orchestrator.should_block_merge()
    print(f"🚦 Should block merge: {'❌ YES' if should_block else '✅ NO'}")
    print()
    
    print("🎉 Demo completed successfully!")
    print("=" * 50)


async def demo_specific_agent():
    """Demonstrate a specific agent's capabilities."""
    
    print("🤖 Specific Agent Demo: Architecture Analyst")
    print("=" * 50)
    
    from .agents.architecture_analyst import ArchitectureAnalyst
    from .agents.base_agent import ReviewContext
    
    # Create sample code with architectural issues
    sample_code = """
from fastapi import FastAPI
import sqlalchemy
from models import User

app = FastAPI()

@app.get("/users")
def get_users():
    # This violates layering - direct DB access in API layer
    users = sqlalchemy.select(User).execute()
    return users

class GodClass:
    def method1(self): pass
    def method2(self): pass
    def method3(self): pass
    def method4(self): pass
    def method5(self): pass
    def method6(self): pass
    def method7(self): pass
    def method8(self): pass
    def method9(self): pass
    def method10(self): pass
    def method11(self): pass
    def method12(self): pass
"""
    
    # Create review context
    context = ReviewContext(
        project_path="/demo",
        memory_bank_path=".memory",
        target_files=["demo.py"],
        review_type="file"
    )
    
    # Initialize agent
    agent = ArchitectureAnalyst()
    
    # Analyze code
    findings = await agent.analyze(sample_code, context)
    
    print(f"📊 Findings: {len(findings)}")
    print()
    
    for finding in findings:
        print(f"🔍 {finding.severity.value} - {finding.category}")
        print(f"   Summary: {finding.summary}")
        print(f"   Recommendation: {finding.recommendation}")
        print()
    
    print("✅ Architecture Analyst demo completed!")


if __name__ == "__main__":
    print("Choose demo mode:")
    print("1. Full system demo")
    print("2. Specific agent demo")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "1":
        asyncio.run(demo_code_review())
    elif choice == "2":
        asyncio.run(demo_specific_agent())
    else:
        print("Invalid choice. Running full system demo...")
        asyncio.run(demo_code_review())
