#!/usr/bin/env python3
"""
Update Memory Demo

Demonstration of the memory update system functionality.
Shows how the system maintains and optimizes project memory.
"""

import asyncio
import sys
from pathlib import Path
from memory_updater import update_memory


async def demo_update_memory():
    """Demonstrate the memory update system."""
    
    print("🎬 AlgoTrading Memory Update System - DEMO")
    print("=" * 60)
    print("🚀 Demonstrating comprehensive memory maintenance...")
    print()
    
    # Get project path
    project_path = str(Path.cwd())
    
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


async def demo_memory_structure():
    """Demonstrate memory structure analysis."""
    
    print("🏗️  MEMORY STRUCTURE ANALYSIS")
    print("=" * 60)
    
    memory_path = Path.cwd() / ".memory"
    
    if not memory_path.exists():
        print("❌ Memory directory not found!")
        return
    
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


async def main():
    """Main demo function."""
    
    if len(sys.argv) > 1 and sys.argv[1] == "structure":
        await demo_memory_structure()
        return 0
    
    # Run full demo
    return await demo_update_memory()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
