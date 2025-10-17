#!/usr/bin/env python3
"""
Update Memory Command

Main entry point for the memory update system.
Usage: python update_memory.py [options]

This command executes a comprehensive maintenance and learning process
on the project memory (.memory/) to keep it updated, coherent, and
usable by all agents (Implementer, Reviewer, Tester, etc.).
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add .memory to path
sys.path.insert(0, str(Path(__file__).parent / ".memory"))

from memory_updater import update_memory


def main():
    """Main function for update memory command."""
    
    parser = argparse.ArgumentParser(
        description="Update project memory - comprehensive maintenance and learning system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python update_memory.py                    # Update memory for current project
  python update_memory.py --demo            # Run demo of memory update system
  python update_memory.py --structure       # Show memory structure analysis
  python update_memory.py --help            # Show this help message

Functions:
  1. Collect recent context from logs, commits, and feedback
  2. Learn from patterns and adjust agent prompts
  3. Clean and optimize memory structure
  4. Validate task and agent integrity
  5. Create consolidated snapshots
        """
    )
    
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run demo of memory update system"
    )
    
    parser.add_argument(
        "--structure",
        action="store_true",
        help="Show memory structure analysis"
    )
    
    parser.add_argument(
        "--project-path",
        type=str,
        help="Path to project root (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Get project path
    project_path = args.project_path or str(Path.cwd())
    
    # Run appropriate function
    if args.demo:
        return asyncio.run(demo_update_memory(project_path))
    elif args.structure:
        return asyncio.run(demo_memory_structure(project_path))
    else:
        return asyncio.run(run_update_memory(project_path))


async def run_update_memory(project_path: str) -> int:
    """Run the memory update process."""
    
    print("🧠 AlgoTrading Memory Update System")
    print("=" * 60)
    print(f"📁 Project Path: {project_path}")
    print()
    
    # Execute memory update
    result = await update_memory(project_path)
    
    # Print final results
    print("📊 FINAL RESULTS:")
    print("=" * 60)
    print(f"✅ Success: {result.success}")
    print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
    print(f"📝 Changes Made: {len(result.changes_made)}")
    print(f"🎓 Lessons Learned: {len(result.lessons_learned)}")
    print(f"⚠️  Issues Found: {len(result.issues_found)}")
    print(f"💡 Recommendations: {len(result.recommendations)}")
    
    if result.snapshot_path:
        print(f"💾 Snapshot: {result.snapshot_path}")
    
    print()
    
    # Print detailed results
    if result.changes_made:
        print("📝 CHANGES MADE:")
        print("-" * 40)
        for change in result.changes_made:
            print(f"✅ {change}")
        print()
    
    if result.lessons_learned:
        print("🎓 LESSONS LEARNED:")
        print("-" * 40)
        for lesson in result.lessons_learned:
            print(f"📚 {lesson}")
        print()
    
    if result.issues_found:
        print("⚠️  ISSUES FOUND:")
        print("-" * 40)
        for issue in result.issues_found:
            print(f"❌ {issue}")
        print()
    
    if result.recommendations:
        print("💡 RECOMMENDATIONS:")
        print("-" * 40)
        for recommendation in result.recommendations:
            print(f"💡 {recommendation}")
        print()
    
    # Final status
    if result.success:
        print("🎉 MEMORY UPDATE COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("✅ Memory is now clean, coherent, and optimized")
        print("✅ All agents have updated prompts and lessons")
        print("✅ Tasks are validated and complete")
        print("✅ Ready for next orchestrator commands")
        print()
        print("🚀 You can now run:")
        print("   orchestrator implement T002")
        print("   code review T002")
        print("   test T002")
        print()
        return 0
    else:
        print("❌ MEMORY UPDATE FAILED!")
        print("=" * 60)
        print("⚠️  Please check the issues above and try again")
        print()
        return 1


async def demo_update_memory(project_path: str) -> int:
    """Run demo of memory update system."""
    
    print("🎬 AlgoTrading Memory Update System - DEMO")
    print("=" * 60)
    print("🚀 Demonstrating comprehensive memory maintenance...")
    print()
    
    print("📋 DEMO OVERVIEW:")
    print("-" * 40)
    print("This demo will show how the Memory Update System:")
    print("1. 📊 Collects recent context from logs, commits, and feedback")
    print("2. 🎓 Learns from patterns and adjusts agent prompts")
    print("3. 🧹 Cleans and optimizes memory structure")
    print("4. ✅ Validates task and agent integrity")
    print("5. 💾 Creates consolidated snapshots")
    print()
    
    # Execute memory update
    print("🔄 EXECUTING MEMORY UPDATE...")
    print("=" * 60)
    
    result = await update_memory(project_path)
    
    # Show detailed results
    print("📊 DEMO RESULTS:")
    print("=" * 60)
    print(f"✅ Success: {result.success}")
    print(f"⏱️  Execution Time: {result.execution_time:.2f}s")
    print()
    
    # Show changes made
    if result.changes_made:
        print("📝 CHANGES MADE:")
        print("-" * 40)
        for i, change in enumerate(result.changes_made, 1):
            print(f"{i:2d}. ✅ {change}")
        print()
    
    # Show lessons learned
    if result.lessons_learned:
        print("🎓 LESSONS LEARNED:")
        print("-" * 40)
        for i, lesson in enumerate(result.lessons_learned, 1):
            print(f"{i:2d}. 📚 {lesson}")
        print()
    
    # Show issues found
    if result.issues_found:
        print("⚠️  ISSUES FOUND:")
        print("-" * 40)
        for i, issue in enumerate(result.issues_found, 1):
            print(f"{i:2d}. ❌ {issue}")
        print()
    
    # Show recommendations
    if result.recommendations:
        print("💡 RECOMMENDATIONS:")
        print("-" * 40)
        for i, recommendation in enumerate(result.recommendations, 1):
            print(f"{i:2d}. 💡 {recommendation}")
        print()
    
    # Show snapshot info
    if result.snapshot_path:
        print("💾 SNAPSHOT CREATED:")
        print("-" * 40)
        print(f"📁 Path: {result.snapshot_path}")
        print("✅ Memory state saved for future reference")
        print()
    
    # Final assessment
    print("🎯 FINAL ASSESSMENT:")
    print("=" * 60)
    
    if result.success:
        print("✅ MEMORY UPDATE SUCCESSFUL!")
        print("✅ Memory is now clean, coherent, and optimized")
        print("✅ All agents have updated prompts and lessons")
        print("✅ Tasks are validated and complete")
        print("✅ Ready for next orchestrator commands")
        print()
        
        print("🚀 NEXT STEPS:")
        print("-" * 40)
        print("You can now run:")
        print("  • orchestrator implement T002")
        print("  • code review T002")
        print("  • test T002")
        print("  • update memory (to maintain coherence)")
        print()
        
        print("🎉 DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        return 0
        
    else:
        print("❌ MEMORY UPDATE FAILED!")
        print("⚠️  Please check the issues above and try again")
        print()
        return 1


async def demo_memory_structure(project_path: str) -> int:
    """Demonstrate memory structure analysis."""
    
    print("🏗️  MEMORY STRUCTURE ANALYSIS")
    print("=" * 60)
    
    memory_path = Path(project_path) / ".memory"
    
    if not memory_path.exists():
        print("❌ Memory directory not found!")
        return 1
    
    print("📁 Memory Directory Structure:")
    print("-" * 40)
    
    # Show directory structure
    for item in sorted(memory_path.iterdir()):
        if item.is_dir():
            print(f"📁 {item.name}/")
            
            # Show subdirectories
            for subitem in sorted(item.iterdir()):
                if subitem.is_dir():
                    print(f"   📁 {subitem.name}/")
                else:
                    print(f"   📄 {subitem.name}")
        else:
            print(f"📄 {item.name}")
    
    print()
    
    # Show file counts
    print("📊 File Statistics:")
    print("-" * 40)
    
    total_files = 0
    total_dirs = 0
    
    for item in memory_path.rglob("*"):
        if item.is_file():
            total_files += 1
        elif item.is_dir():
            total_dirs += 1
    
    print(f"📄 Total Files: {total_files}")
    print(f"📁 Total Directories: {total_dirs}")
    print(f"📁 Memory Size: {memory_path.stat().st_size} bytes")
    print()
    
    # Show key directories
    print("🔑 Key Directories:")
    print("-" * 40)
    
    key_dirs = {
        "tasks": "Task definitions and specifications",
        "prompts": "Agent prompts and instructions",
        "lessons": "Lessons learned from implementations",
        "checkpoints": "Memory snapshots and backups",
        "code_review": "Code review system",
        "testing": "Testing system",
        "specs": "Project specifications"
    }
    
    for dir_name, description in key_dirs.items():
        dir_path = memory_path / dir_name
        if dir_path.exists():
            file_count = len(list(dir_path.rglob("*")))
            print(f"✅ {dir_name}/ - {description} ({file_count} items)")
        else:
            print(f"❌ {dir_name}/ - {description} (missing)")
    
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
