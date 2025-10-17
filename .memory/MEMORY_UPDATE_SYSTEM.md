# Memory Update System

## Overview

The Memory Update System is a comprehensive maintenance and learning system for project memory (`.memory/`). It keeps memory updated, coherent, and usable by all agents (Implementer, Reviewer, Tester, etc.).

## Functions

### 1. Collect Recent Context

Scans task execution logs (`/logs/tasks/`), commits, and human feedback.

- Detects recent changes in code, test results, and reviewer comments
- Analyzes active branches (e.g., `feature/T001`) and recent merges to main
- Collects context from git history and file changes

### 2. Contextual Learning

Identifies error patterns and improvements detected.

- Adjusts base prompts of agents (`/memory/prompts/agents/`) to reflect lessons learned
- Adds new entries in `/memory/lessons/` like `lesson_T001.md` with:
  - What was done
  - What was learned
  - What was corrected
  - What is recommended for next time

### 3. Cleanup and Optimization

Removes empty folders, duplicates, and old version files.

- **Integrity Validation**: Checks that all tasks (T000x) have:
  - Objective
  - Inputs
  - Expected outputs
  - Satisfied dependencies
- Verifies that no agent has orphaned or empty prompts

### 4. Final Consolidation

Saves everything in a new snapshot:

- `.memory/checkpoints/update_YYYYMMDD.json`
- Registers a summary of changes and improvements
- Leaves everything ready for the next orchestrator command

## Usage

### Basic Usage

```bash
# Update memory for current project
python update_memory.py

# Run demo of memory update system
python update_memory.py --demo

# Show memory structure analysis
python update_memory.py --structure

# Update memory for specific project
python update_memory.py --project-path /path/to/project
```

### Expected Result

After execution:

- `.memory` is clean, coherent, self-contained, and versioned
- Each agent's prompts reflect the latest lessons learned
- Tasks are complete and verified
- Empty folders and redundancies are eliminated
- Warnings if any section of `.memory` is incomplete or out of sync

## System Architecture

### Core Components

1. **MemoryUpdater**: Main orchestrator class
2. **MemoryUpdateResult**: Result data structure
3. **TaskValidation**: Task integrity validation
4. **AgentValidation**: Agent integrity validation

### Process Flow

```
1. Collect Recent Context
   ├── Scan task logs
   ├── Analyze git commits
   ├── Check active branches
   ├── Detect code changes
   └── Collect test results

2. Contextual Learning
   ├── Identify error patterns
   ├── Identify improvement patterns
   ├── Update agent prompts
   └── Create lesson entries

3. Cleanup and Optimization
   ├── Remove empty directories
   ├── Remove duplicates
   ├── Remove old versions
   └── Optimize file structure

4. Integrity Validation
   ├── Validate tasks
   ├── Validate agents
   └── Check dependencies

5. Final Consolidation
   ├── Create snapshot
   ├── Generate summary
   └── Final validation
```

## Integration with Agents

### Code Review Agents

- Prompts updated with latest architectural patterns
- Lessons learned from previous reviews integrated
- Error patterns from reviews identified and addressed

### Testing Agents

- Test patterns and strategies updated
- Common failure modes documented
- Auto-fixer strategies improved

### Project Conductor

- Task dependencies validated
- Implementation patterns learned
- Coordination strategies optimized

## File Structure

```
.memory/
├── memory_updater.py          # Core update system
├── update_memory.py           # Main entry point
├── update_memory_demo.py      # Demo system
├── MEMORY_UPDATE_SYSTEM.md    # This documentation
├── tasks/                     # Task definitions
├── prompts/                   # Agent prompts
├── lessons/                   # Lessons learned
├── checkpoints/               # Memory snapshots
├── code_review/               # Code review system
├── testing/                   # Testing system
└── specs/                     # Project specifications
```

## Examples

### Example Usage

```bash
# After implementing T001
python update_memory.py

# Output:
# 🧠 AlgoTrading Memory Update System
# ============================================================
# 📊 Phase 1: Collecting Recent Context
# ✅ Collected 5 task execution logs
# ✅ Analyzed 3 recent commits
# ✅ Found 2 active branches
# ✅ Detected 15 code changes
# ✅ Analyzed 2 test results
#
# 🎓 Phase 2: Contextual Learning
# ✅ Identified 2 error patterns
# ✅ Identified 3 improvement patterns
# ✅ Updated 4 agent prompts
# ✅ Created 1 lesson entries
#
# 🧹 Phase 3: Cleanup and Optimization
# ✅ Removed 2 empty directories
# ✅ Removed 1 duplicate files
# ✅ Removed 3 old version files
# ✅ Optimized file structure
#
# ✅ Phase 4: Integrity Validation
# ✅ All tasks are complete
# ✅ All agents are properly configured
# ✅ All dependencies are satisfied
#
# 💾 Phase 5: Final Consolidation
# ✅ Created snapshot: .memory/checkpoints/update_20241201_143022.json
# ✅ Generated update summary
# ✅ Final validation passed
#
# 🎉 Memory Update Completed Successfully!
# ============================================================
# ⏱️  Execution Time: 2.34s
# 📝 Changes Made: 12
# 🎓 Lessons Learned: 5
# ⚠️  Issues Found: 0
# 💡 Recommendations: 3
```

### Example Lesson Entry

```markdown
# Lesson Learned - T001

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

2024-12-01 14:30:22
```

## Benefits

### For Agents

- **Updated Prompts**: Agents have access to latest lessons and patterns
- **Reduced Errors**: Common error patterns are identified and addressed
- **Improved Performance**: Optimized memory structure improves access speed
- **Better Coordination**: Dependencies and relationships are validated

### For Project

- **Coherent Memory**: All memory is consistent and up-to-date
- **Learning Continuity**: Lessons from previous tasks are preserved
- **Quality Assurance**: Integrity validation ensures completeness
- **Version Control**: Snapshots provide rollback capability

### For Development

- **Faster Iterations**: Clean memory structure improves agent performance
- **Better Planning**: Validated dependencies enable better task planning
- **Reduced Bugs**: Learned patterns help prevent common issues
- **Improved Coordination**: All agents work with consistent information

## Maintenance

### Regular Updates

Run `update memory` after:

- Completing major tasks
- Significant code changes
- Agent system updates
- Before starting new development cycles

### Monitoring

- Check update summaries for issues
- Review lesson entries for patterns
- Monitor snapshot sizes and frequency
- Validate agent performance after updates

## Troubleshooting

### Common Issues

1. **Memory Update Fails**

   - Check file permissions
   - Verify git repository status
   - Ensure sufficient disk space

2. **Agents Not Updated**

   - Check prompt file permissions
   - Verify lesson entries are created
   - Review agent validation results

3. **Tasks Incomplete**
   - Check task file format
   - Verify required sections exist
   - Review dependency definitions

### Recovery

If memory update fails:

1. Check the last successful snapshot
2. Review error messages in update summary
3. Fix identified issues
4. Re-run update memory
5. Verify all systems are operational

## Future Enhancements

- **Machine Learning Integration**: Use ML to identify patterns
- **Automated Prompt Generation**: Generate prompts based on lessons
- **Predictive Analysis**: Predict potential issues before they occur
- **Cross-Project Learning**: Share lessons across multiple projects
- **Real-time Updates**: Update memory in real-time during development
