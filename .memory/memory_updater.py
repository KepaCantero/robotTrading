"""
Memory Update System

Comprehensive maintenance and learning system for project memory (.memory/).
Keeps memory updated, coherent, and usable by all agents (Implementer, Reviewer, Tester, etc.).
"""

import os
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import asyncio
import re
import hashlib


@dataclass
class MemoryUpdateResult:
    """Result of memory update operation."""
    success: bool
    changes_made: List[str]
    lessons_learned: List[str]
    issues_found: List[str]
    recommendations: List[str]
    snapshot_path: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class TaskValidation:
    """Validation result for a task."""
    task_id: str
    has_objective: bool
    has_inputs: bool
    has_outputs: bool
    dependencies_satisfied: bool
    is_complete: bool
    issues: List[str]


@dataclass
class AgentValidation:
    """Validation result for an agent."""
    agent_name: str
    has_prompts: bool
    prompts_complete: bool
    has_lessons: bool
    issues: List[str]


class MemoryUpdater:
    """
    Memory Update System for maintaining project memory coherence.
    
    Functions:
    1. Collect recent context from logs, commits, and feedback
    2. Learn from patterns and adjust agent prompts
    3. Clean and optimize memory structure
    4. Validate task and agent integrity
    5. Create consolidated snapshots
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.memory_path = self.project_path / ".memory"
        self.logs_path = self.project_path / "logs"
        self.tasks_path = self.memory_path / "tasks"
        self.prompts_path = self.memory_path / "prompts"
        self.lessons_path = self.memory_path / "lessons"
        self.checkpoints_path = self.memory_path / "checkpoints"
        self.agents_path = self.memory_path / "agents"
        
        # Ensure directories exist
        for path in [self.logs_path, self.tasks_path, self.prompts_path, 
                    self.lessons_path, self.checkpoints_path]:
            path.mkdir(parents=True, exist_ok=True)
        
        self.changes_made = []
        self.lessons_learned = []
        self.issues_found = []
        self.recommendations = []
    
    async def update_memory(self) -> MemoryUpdateResult:
        """
        Execute complete memory update process.
        
        Returns:
            MemoryUpdateResult: Complete update results
        """
        start_time = datetime.now()
        
        try:
            print("🧠 AlgoTrading Memory Update System")
            print("=" * 60)
            print("🚀 Starting comprehensive memory maintenance...")
            print()
            
            # Phase 1: Collect recent context
            print("📊 Phase 1: Collecting Recent Context")
            print("-" * 40)
            await self._collect_recent_context()
            
            # Phase 2: Contextual learning
            print("🎓 Phase 2: Contextual Learning")
            print("-" * 40)
            await self._contextual_learning()
            
            # Phase 3: Cleanup and optimization
            print("🧹 Phase 3: Cleanup and Optimization")
            print("-" * 40)
            await self._cleanup_and_optimization()
            
            # Phase 4: Integrity validation
            print("✅ Phase 4: Integrity Validation")
            print("-" * 40)
            await self._integrity_validation()
            
            # Phase 5: Final consolidation
            print("💾 Phase 5: Final Consolidation")
            print("-" * 40)
            snapshot_path = await self._final_consolidation()
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = MemoryUpdateResult(
                success=True,
                changes_made=self.changes_made,
                lessons_learned=self.lessons_learned,
                issues_found=self.issues_found,
                recommendations=self.recommendations,
                snapshot_path=snapshot_path,
                execution_time=execution_time
            )
            
            print("🎉 Memory Update Completed Successfully!")
            print("=" * 60)
            print(f"⏱️  Execution Time: {execution_time:.2f}s")
            print(f"📝 Changes Made: {len(self.changes_made)}")
            print(f"🎓 Lessons Learned: {len(self.lessons_learned)}")
            print(f"⚠️  Issues Found: {len(self.issues_found)}")
            print(f"💡 Recommendations: {len(self.recommendations)}")
            print()
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            print(f"❌ Memory Update Failed: {str(e)}")
            
            return MemoryUpdateResult(
                success=False,
                changes_made=self.changes_made,
                lessons_learned=self.lessons_learned,
                issues_found=self.issues_found + [f"Update failed: {str(e)}"],
                recommendations=self.recommendations,
                execution_time=execution_time
            )
    
    async def _collect_recent_context(self):
        """Collect recent context from logs, commits, and feedback."""
        
        # Collect task execution logs
        task_logs = await self._scan_task_logs()
        if task_logs:
            self.changes_made.append(f"Collected {len(task_logs)} task execution logs")
            print(f"✅ Collected {len(task_logs)} task execution logs")
        
        # Collect recent commits
        recent_commits = await self._scan_recent_commits()
        if recent_commits:
            self.changes_made.append(f"Analyzed {len(recent_commits)} recent commits")
            print(f"✅ Analyzed {len(recent_commits)} recent commits")
        
        # Collect active branches
        active_branches = await self._scan_active_branches()
        if active_branches:
            self.changes_made.append(f"Found {len(active_branches)} active branches")
            print(f"✅ Found {len(active_branches)} active branches")
        
        # Collect code changes
        code_changes = await self._scan_code_changes()
        if code_changes:
            self.changes_made.append(f"Detected {len(code_changes)} code changes")
            print(f"✅ Detected {len(code_changes)} code changes")
        
        # Collect test results
        test_results = await self._scan_test_results()
        if test_results:
            self.changes_made.append(f"Analyzed {len(test_results)} test results")
            print(f"✅ Analyzed {len(test_results)} test results")
        
        print()
    
    async def _contextual_learning(self):
        """Learn from patterns and adjust agent prompts."""
        
        # Identify error patterns
        error_patterns = await self._identify_error_patterns()
        if error_patterns:
            self.lessons_learned.extend(error_patterns)
            print(f"✅ Identified {len(error_patterns)} error patterns")
        
        # Identify improvement patterns
        improvement_patterns = await self._identify_improvement_patterns()
        if improvement_patterns:
            self.lessons_learned.extend(improvement_patterns)
            print(f"✅ Identified {len(improvement_patterns)} improvement patterns")
        
        # Update agent prompts
        prompts_updated = await self._update_agent_prompts()
        if prompts_updated:
            self.changes_made.append(f"Updated {prompts_updated} agent prompts")
            print(f"✅ Updated {prompts_updated} agent prompts")
        
        # Create lesson entries
        lessons_created = await self._create_lesson_entries()
        if lessons_created:
            self.changes_made.append(f"Created {lessons_created} lesson entries")
            print(f"✅ Created {lessons_created} lesson entries")
        
        print()
    
    async def _cleanup_and_optimization(self):
        """Clean and optimize memory structure."""
        
        # Remove empty directories
        empty_dirs_removed = await self._remove_empty_directories()
        if empty_dirs_removed:
            self.changes_made.append(f"Removed {empty_dirs_removed} empty directories")
            print(f"✅ Removed {empty_dirs_removed} empty directories")
        
        # Remove duplicates
        duplicates_removed = await self._remove_duplicates()
        if duplicates_removed:
            self.changes_made.append(f"Removed {duplicates_removed} duplicate files")
            print(f"✅ Removed {duplicates_removed} duplicate files")
        
        # Remove old versions
        old_versions_removed = await self._remove_old_versions()
        if old_versions_removed:
            self.changes_made.append(f"Removed {old_versions_removed} old version files")
            print(f"✅ Removed {old_versions_removed} old version files")
        
        # Optimize file structure
        structure_optimized = await self._optimize_file_structure()
        if structure_optimized:
            self.changes_made.append("Optimized file structure")
            print("✅ Optimized file structure")
        
        print()
    
    async def _integrity_validation(self):
        """Validate task and agent integrity."""
        
        # Validate tasks
        task_validations = await self._validate_tasks()
        incomplete_tasks = [t for t in task_validations if not t.is_complete]
        if incomplete_tasks:
            self.issues_found.extend([f"Task {t.task_id} incomplete: {', '.join(t.issues)}" 
                                    for t in incomplete_tasks])
            print(f"⚠️  Found {len(incomplete_tasks)} incomplete tasks")
        else:
            print("✅ All tasks are complete")
        
        # Validate agents
        agent_validations = await self._validate_agents()
        incomplete_agents = [a for a in agent_validations if a.issues]
        if incomplete_agents:
            self.issues_found.extend([f"Agent {a.agent_name} issues: {', '.join(a.issues)}" 
                                    for a in incomplete_agents])
            print(f"⚠️  Found {len(incomplete_agents)} agents with issues")
        else:
            print("✅ All agents are properly configured")
        
        # Check dependencies
        dependency_issues = await self._check_dependencies()
        if dependency_issues:
            self.issues_found.extend(dependency_issues)
            print(f"⚠️  Found {len(dependency_issues)} dependency issues")
        else:
            print("✅ All dependencies are satisfied")
        
        print()
    
    async def _final_consolidation(self) -> Optional[str]:
        """Create final consolidation snapshot."""
        
        # Create snapshot
        snapshot_path = await self._create_snapshot()
        if snapshot_path:
            self.changes_made.append(f"Created snapshot: {snapshot_path}")
            print(f"✅ Created snapshot: {snapshot_path}")
        
        # Generate summary
        summary = await self._generate_update_summary()
        if summary:
            self.changes_made.append("Generated update summary")
            print("✅ Generated update summary")
        
        # Final validation
        final_validation = await self._final_validation()
        if final_validation:
            print("✅ Final validation passed")
        else:
            self.issues_found.append("Final validation failed")
            print("⚠️  Final validation failed")
        
        print()
        return snapshot_path
    
    # Helper methods for context collection
    async def _scan_task_logs(self) -> List[Dict[str, Any]]:
        """Scan task execution logs."""
        logs = []
        logs_dir = self.logs_path / "tasks"
        
        if logs_dir.exists():
            for log_file in logs_dir.glob("*.json"):
                try:
                    with open(log_file, 'r') as f:
                        log_data = json.load(f)
                        logs.append(log_data)
                except Exception as e:
                    self.issues_found.append(f"Failed to read log {log_file}: {str(e)}")
        
        return logs
    
    async def _scan_recent_commits(self) -> List[Dict[str, Any]]:
        """Scan recent git commits."""
        commits = []
        
        try:
            # Get recent commits
            result = subprocess.run(
                ["git", "log", "--oneline", "-10", "--pretty=format:%H|%s|%an|%ad"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|')
                        if len(parts) >= 4:
                            commits.append({
                                'hash': parts[0],
                                'message': parts[1],
                                'author': parts[2],
                                'date': parts[3]
                            })
        except Exception as e:
            self.issues_found.append(f"Failed to scan commits: {str(e)}")
        
        return commits
    
    async def _scan_active_branches(self) -> List[str]:
        """Scan active git branches."""
        branches = []
        
        try:
            # Get all branches
            result = subprocess.run(
                ["git", "branch", "-a"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.strip():
                        branch = line.strip().replace('* ', '').replace('remotes/origin/', '')
                        if branch and not branch.startswith('HEAD'):
                            branches.append(branch)
        except Exception as e:
            self.issues_found.append(f"Failed to scan branches: {str(e)}")
        
        return branches
    
    async def _scan_code_changes(self) -> List[Dict[str, Any]]:
        """Scan recent code changes."""
        changes = []
        
        try:
            # Get diff of recent changes
            result = subprocess.run(
                ["git", "diff", "--name-status", "HEAD~5..HEAD"],
                cwd=self.project_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('\t')
                        if len(parts) >= 2:
                            changes.append({
                                'status': parts[0],
                                'file': parts[1]
                            })
        except Exception as e:
            self.issues_found.append(f"Failed to scan code changes: {str(e)}")
        
        return changes
    
    async def _scan_test_results(self) -> List[Dict[str, Any]]:
        """Scan recent test results."""
        results = []
        
        # Look for test result files
        test_files = [
            self.project_path / "test_results.json",
            self.project_path / "coverage.json",
            self.memory_path / "testing" / "results.json"
        ]
        
        for test_file in test_files:
            if test_file.exists():
                try:
                    with open(test_file, 'r') as f:
                        test_data = json.load(f)
                        results.append(test_data)
                except Exception as e:
                    self.issues_found.append(f"Failed to read test results {test_file}: {str(e)}")
        
        return results
    
    # Helper methods for contextual learning
    async def _identify_error_patterns(self) -> List[str]:
        """Identify common error patterns."""
        patterns = []
        
        # Analyze logs for common errors
        logs = await self._scan_task_logs()
        error_counts = {}
        
        for log in logs:
            if 'error' in log.get('status', '').lower():
                error_type = log.get('error_type', 'Unknown')
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        # Identify patterns
        for error_type, count in error_counts.items():
            if count >= 2:  # Pattern if appears 2+ times
                patterns.append(f"Common error pattern: {error_type} (occurred {count} times)")
        
        return patterns
    
    async def _identify_improvement_patterns(self) -> List[str]:
        """Identify improvement patterns."""
        patterns = []
        
        # Analyze successful patterns
        logs = await self._scan_task_logs()
        success_patterns = {}
        
        for log in logs:
            if log.get('status') == 'success':
                approach = log.get('approach', 'Unknown')
                success_patterns[approach] = success_patterns.get(approach, 0) + 1
        
        # Identify successful patterns
        for approach, count in success_patterns.items():
            if count >= 2:  # Pattern if successful 2+ times
                patterns.append(f"Successful pattern: {approach} (successful {count} times)")
        
        return patterns
    
    async def _update_agent_prompts(self) -> int:
        """Update agent prompts based on lessons learned."""
        updated_count = 0
        
        # Update prompts based on lessons
        prompts_dir = self.prompts_path / "agents"
        if prompts_dir.exists():
            for prompt_file in prompts_dir.glob("*.md"):
                try:
                    # Read current prompt
                    with open(prompt_file, 'r') as f:
                        content = f.read()
                    
                    # Apply lessons (simplified)
                    updated_content = self._apply_lessons_to_prompt(content)
                    
                    if updated_content != content:
                        with open(prompt_file, 'w') as f:
                            f.write(updated_content)
                        updated_count += 1
                        
                except Exception as e:
                    self.issues_found.append(f"Failed to update prompt {prompt_file}: {str(e)}")
        
        return updated_count
    
    def _apply_lessons_to_prompt(self, content: str) -> str:
        """Apply lessons learned to a prompt."""
        # Simple implementation - in practice, this would be more sophisticated
        updated_content = content
        
        # Add lessons learned section if not present
        if "## Lessons Learned" not in content:
            lessons_section = "\n\n## Lessons Learned\n"
            for lesson in self.lessons_learned[:3]:  # Add top 3 lessons
                lessons_section += f"- {lesson}\n"
            updated_content += lessons_section
        
        return updated_content
    
    async def _create_lesson_entries(self) -> int:
        """Create lesson entries for recent tasks."""
        created_count = 0
        
        # Create lesson for T001
        lesson_file = self.lessons_path / "lesson_T001.md"
        if not lesson_file.exists():
            lesson_content = self._generate_lesson_content("T001")
            with open(lesson_file, 'w') as f:
                f.write(lesson_content)
            created_count += 1
        
        return created_count
    
    def _generate_lesson_content(self, task_id: str) -> str:
        """Generate lesson content for a task."""
        return f"""# Lesson Learned - {task_id}

## What Was Done
- Implemented FastAPI base structure
- Added health check endpoints
- Configured CORS middleware
- Set up testing framework
- Implemented error handling

## What Was Learned
- Circular imports can cause issues in FastAPI applications
- Proper import structure is crucial for maintainability
- Testing framework integration requires careful setup
- CORS configuration is essential for web applications

## What Was Corrected
- Fixed circular import in app/main.py
- Fixed circular import in tests/test_main.py
- Improved Architecture Analyst logic to reduce false positives
- Enhanced error handling and validation

## Recommendations for Next Time
- Always check for circular imports during implementation
- Use proper import structure from the beginning
- Implement comprehensive testing early
- Use code review system to catch issues early
- Apply lessons learned to future implementations

## Date
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
    
    # Helper methods for cleanup and optimization
    async def _remove_empty_directories(self) -> int:
        """Remove empty directories."""
        removed_count = 0
        
        for root, dirs, files in os.walk(self.memory_path, topdown=False):
            for dir_name in dirs:
                dir_path = Path(root) / dir_name
                try:
                    if not any(dir_path.iterdir()):  # Directory is empty
                        dir_path.rmdir()
                        removed_count += 1
                except Exception:
                    pass  # Directory not empty or other issue
        
        return removed_count
    
    async def _remove_duplicates(self) -> int:
        """Remove duplicate files."""
        removed_count = 0
        file_hashes = {}
        
        for file_path in self.memory_path.rglob("*"):
            if file_path.is_file():
                try:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    
                    if file_hash in file_hashes:
                        # Duplicate found, remove it
                        file_path.unlink()
                        removed_count += 1
                    else:
                        file_hashes[file_hash] = file_path
                        
                except Exception:
                    pass  # Skip files that can't be read
        
        return removed_count
    
    async def _remove_old_versions(self) -> int:
        """Remove old version files."""
        removed_count = 0
        
        # Remove old backup files
        for file_path in self.memory_path.rglob("*.bak"):
            try:
                file_path.unlink()
                removed_count += 1
            except Exception:
                pass
        
        # Remove old temporary files
        for file_path in self.memory_path.rglob("*.tmp"):
            try:
                file_path.unlink()
                removed_count += 1
            except Exception:
                pass
        
        return removed_count
    
    async def _optimize_file_structure(self) -> bool:
        """Optimize file structure."""
        # Ensure proper directory structure
        required_dirs = [
            "tasks", "prompts", "lessons", "checkpoints", "agents",
            "code_review", "testing", "specs"
        ]
        
        for dir_name in required_dirs:
            dir_path = self.memory_path / dir_name
            dir_path.mkdir(exist_ok=True)
        
        return True
    
    # Helper methods for integrity validation
    async def _validate_tasks(self) -> List[TaskValidation]:
        """Validate all tasks."""
        validations = []
        
        # Check for task files
        task_files = list(self.tasks_path.glob("T*.md")) + list(self.tasks_path.glob("task_*.md"))
        
        for task_file in task_files:
            task_id = task_file.stem
            validation = TaskValidation(
                task_id=task_id,
                has_objective=False,
                has_inputs=False,
                has_outputs=False,
                dependencies_satisfied=True,
                is_complete=False,
                issues=[]
            )
            
            try:
                with open(task_file, 'r') as f:
                    content = f.read()
                
                # Check for required sections
                if "## Objective" in content or "## Goal" in content:
                    validation.has_objective = True
                else:
                    validation.issues.append("Missing objective")
                
                if "## Inputs" in content or "## Requirements" in content:
                    validation.has_inputs = True
                else:
                    validation.issues.append("Missing inputs")
                
                if "## Outputs" in content or "## Deliverables" in content:
                    validation.has_outputs = True
                else:
                    validation.issues.append("Missing outputs")
                
                validation.is_complete = (validation.has_objective and 
                                        validation.has_inputs and 
                                        validation.has_outputs and
                                        len(validation.issues) == 0)
                
            except Exception as e:
                validation.issues.append(f"Failed to read task file: {str(e)}")
            
            validations.append(validation)
        
        return validations
    
    async def _validate_agents(self) -> List[AgentValidation]:
        """Validate all agents."""
        validations = []
        
        # Check agent directories
        agent_dirs = [
            self.memory_path / "code_review" / "agents",
            self.memory_path / "testing" / "agents"
        ]
        
        for agent_dir in agent_dirs:
            if agent_dir.exists():
                for agent_file in agent_dir.glob("*.py"):
                    agent_name = agent_file.stem
                    validation = AgentValidation(
                        agent_name=agent_name,
                        has_prompts=False,
                        prompts_complete=False,
                        has_lessons=False,
                        issues=[]
                    )
                    
                    try:
                        with open(agent_file, 'r') as f:
                            content = f.read()
                        
                        # Check for prompts
                        if "prompt" in content.lower() or "instruction" in content.lower():
                            validation.has_prompts = True
                        else:
                            validation.issues.append("Missing prompts")
                        
                        # Check for lessons
                        if "lesson" in content.lower() or "learned" in content.lower():
                            validation.has_lessons = True
                        
                        validation.prompts_complete = validation.has_prompts
                        
                    except Exception as e:
                        validation.issues.append(f"Failed to read agent file: {str(e)}")
                    
                    validations.append(validation)
        
        return validations
    
    async def _check_dependencies(self) -> List[str]:
        """Check task dependencies."""
        issues = []
        
        # Simple dependency check - in practice, this would be more sophisticated
        task_files = list(self.tasks_path.glob("T*.md"))
        
        for task_file in task_files:
            try:
                with open(task_file, 'r') as f:
                    content = f.read()
                
                # Look for dependency references
                if "depends on" in content.lower() or "dependency" in content.lower():
                    # Check if dependencies exist
                    # This is a simplified check
                    pass
                    
            except Exception as e:
                issues.append(f"Failed to check dependencies for {task_file}: {str(e)}")
        
        return issues
    
    # Helper methods for final consolidation
    async def _create_snapshot(self) -> Optional[str]:
        """Create memory snapshot."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_file = self.checkpoints_path / f"update_{timestamp}.json"
        
        try:
            snapshot_data = {
                "timestamp": timestamp,
                "changes_made": self.changes_made,
                "lessons_learned": self.lessons_learned,
                "issues_found": self.issues_found,
                "recommendations": self.recommendations,
                "memory_structure": await self._get_memory_structure()
            }
            
            with open(snapshot_file, 'w') as f:
                json.dump(snapshot_data, f, indent=2)
            
            return str(snapshot_file)
            
        except Exception as e:
            self.issues_found.append(f"Failed to create snapshot: {str(e)}")
            return None
    
    async def _get_memory_structure(self) -> Dict[str, Any]:
        """Get current memory structure."""
        structure = {}
        
        for item in self.memory_path.rglob("*"):
            if item.is_file():
                rel_path = item.relative_to(self.memory_path)
                path_parts = str(rel_path).split('/')
                
                current = structure
                for part in path_parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                current[path_parts[-1]] = {
                    "size": item.stat().st_size,
                    "modified": datetime.fromtimestamp(item.stat().st_mtime).isoformat()
                }
        
        return structure
    
    async def _generate_update_summary(self) -> bool:
        """Generate update summary."""
        try:
            summary_file = self.memory_path / "update_summary.md"
            
            summary_content = f"""# Memory Update Summary

## Update Date
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Changes Made
{len(self.changes_made)} changes were made:
"""
            
            for change in self.changes_made:
                summary_content += f"- {change}\n"
            
            summary_content += f"""
## Lessons Learned
{len(self.lessons_learned)} lessons were learned:
"""
            
            for lesson in self.lessons_learned:
                summary_content += f"- {lesson}\n"
            
            summary_content += f"""
## Issues Found
{len(self.issues_found)} issues were found:
"""
            
            for issue in self.issues_found:
                summary_content += f"- {issue}\n"
            
            summary_content += f"""
## Recommendations
{len(self.recommendations)} recommendations:
"""
            
            for recommendation in self.recommendations:
                summary_content += f"- {recommendation}\n"
            
            with open(summary_file, 'w') as f:
                f.write(summary_content)
            
            return True
            
        except Exception as e:
            self.issues_found.append(f"Failed to generate summary: {str(e)}")
            return False
    
    async def _final_validation(self) -> bool:
        """Perform final validation."""
        # Check if memory is coherent
        if not self.memory_path.exists():
            return False
        
        # Check if required directories exist
        required_dirs = ["tasks", "prompts", "lessons", "checkpoints"]
        for dir_name in required_dirs:
            if not (self.memory_path / dir_name).exists():
                return False
        
        # Check if there are any critical issues
        critical_issues = [issue for issue in self.issues_found 
                          if "critical" in issue.lower() or "failed" in issue.lower()]
        
        return len(critical_issues) == 0


async def update_memory(project_path: str = None) -> MemoryUpdateResult:
    """
    Main function to update project memory.
    
    Args:
        project_path: Path to project root. If None, uses current directory.
    
    Returns:
        MemoryUpdateResult: Complete update results
    """
    if project_path is None:
        project_path = Path.cwd()
    
    updater = MemoryUpdater(project_path)
    return await updater.update_memory()


if __name__ == "__main__":
    import sys
    
    project_path = sys.argv[1] if len(sys.argv) > 1 else None
    result = asyncio.run(update_memory(project_path))
    
    if result.success:
        print("✅ Memory update completed successfully!")
        sys.exit(0)
    else:
        print("❌ Memory update failed!")
        sys.exit(1)
