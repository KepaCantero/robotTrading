#!/usr/bin/env python3
"""
Update Memory Command

Main entry point for the memory update system.
Usage: python update_memory.py [project_path]
"""

import sys
import asyncio
from pathlib import Path
from memory_updater import update_memory


async def main():
    """Main function for update memory command."""
    
    # Get project path from command line or use current directory
    project_path = sys.argv[1] if len(sys.argv) > 1 else str(Path.cwd())
    
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


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
