# Project Conductor Agent (T037)

Orchestrates all development workflows (implement, code review, test, merge) across the AlgoTrading MVP tasks (T001–T036) using existing agent systems and Cursor's agentic capabilities.

## 🎯 Mission

Coordinate a full, autonomous implementation lifecycle for any requested task — ensuring context consistency, branch isolation, quality assurance, and production readiness.

## 🧩 Architecture

The Project Conductor **reuses and coordinates** existing agent systems:

### Existing Systems Integrated

1. **Code Review System** (`.memory/code_review/`)

   - 7 specialized agents for code analysis
   - Architecture, Algorithm, Quality, Testing, Security, CI/CD reviewers
   - Comprehensive report generation

2. **Testing System** (`.memory/testing/`)

   - 7 specialized agents for test execution
   - Test Executor, Failure Diagnostician, Auto-Fixer, Integration Verifier
   - Automated fixing and validation

3. **Multi-Agent Orchestrator** (`.memory/specs/agents/`)
   - Complete workflow specifications
   - 8-phase development lifecycle
   - Quality gates and success criteria

## 🚀 Usage

### Basic Command

```bash
implement T0XX
```

### Example

```bash
implement T001
```

## 🧾 Complete Workflow

When you type `implement T0XX`, the following agentic sequence executes:

### 🧬 1️⃣ Preparation Phase

**Agents involved**: Memory Analyst, Planner Agent, Branch Manager

**Steps**:

- **Memory Analyst**: Read `.memory` context and extract all info relevant to task T0XX
- **Planner Agent**: Outline exact subtasks and implementation plan
- **Branch Manager**: Create new branch `feature/T0XX-task-name`

### ⚙️ 2️⃣ Implementation Phase

**Agents involved**: Developer Agent, Documentation Agent

**Steps**:

- **Developer Agent**: Implement the task in code using context from `.memory`
- **Documentation Agent**: Update docstrings, comments, and README sections

### 🧪 3️⃣ Code Review Phase

**Agents involved**: Code Reviewer, Security Auditor, Performance Analyst

**Steps**:

- **Code Reviewer**: Evaluate readability, maintainability, and architecture consistency
- **Security Auditor**: Scan for potential leaks, insecure API calls, or missing validation
- **Performance Analyst**: Analyze complexity and ensure endpoint latency <100ms

### 🧩 4️⃣ Testing Phase

**Agents involved**: QA Tester, Fixer Agent, Load Tester

**Steps**:

- **QA Tester**: Run all new and existing tests using pytest -v
- **Fixer Agent**: If any test fails, automatically fix issues without breaking logic
- **Load Tester**: Execute performance and stress tests

### 🚀 5️⃣ Merge & Deployment Phase

**Agents involved**: Release Manager, CI/CD Agent

**Steps**:

- **Release Manager**: Merge branch → main with proper commit convention
- **CI/CD Agent**: Validate build, run post-merge smoke tests, deploy to staging

## 📊 Output Format

### Execution Report

```json
{
  "task_id": "T001",
  "execution_summary": {
    "start_time": "2025-01-14T10:00:00Z",
    "end_time": "2025-01-14T10:15:00Z",
    "total_phases": 8,
    "overall_status": true
  },
  "phase_results": {
    "memory_analysis": { "status": "completed" },
    "environment_setup": { "branch_name": "feature/T001-fastapi-base" },
    "implementation": { "files_created": ["app/main.py"] },
    "code_review": { "critical_findings": 0 },
    "testing": { "all_tests_passed": true },
    "validation": { "quality_gates_passed": true }
  },
  "quality_metrics": {
    "code_quality": true,
    "test_quality": true,
    "coverage_quality": true
  },
  "next_steps": [
    "✅ Task implementation completed successfully",
    "🔄 Ready for human review and merge"
  ]
}
```

## 🔐 Guardrails & Quality Policies

### Commit Policy

- 1 commit per major subtask
- Branch naming: `feature/`, `fix/`, `test/`
- No direct commits to main
- Merge only after passing review + tests

### Quality Gates

- **Code Quality**: Black formatting, Ruff linting, MyPy type checking
- **Test Quality**: >90% coverage, all tests passing
- **Security**: No critical vulnerabilities
- **Performance**: <100ms endpoint latency

### Automatic Rollback

- If CI/CD fails
- If coverage <90%
- If critical security issues found

### Security Lock

- Agents cannot modify risk algorithms or production secrets without `[APPROVED_CHANGE]` tag

## 🧩 Agent Roles (Reused from Existing Systems)

### From Code Review System

- 🧑‍💻 **Lead Reviewer** - Coordinates code review process
- 🧠 **Architecture Analyst** - Validates architectural compliance
- 🧮 **Algorithm Expert** - Reviews algorithmic correctness
- 🧱 **Code Quality Specialist** - Ensures code quality standards
- 🧪 **Testing Reviewer** - Validates test coverage and quality
- 🔒 **Security Auditor** - Identifies security vulnerabilities
- ⚙️ **CI/CD Verifier** - Validates deployment readiness

### From Testing System

- 🧑‍🔬 **Lead Tester** - Coordinates testing process
- ⚙️ **Test Executor** - Executes tests and captures results
- 🧠 **Failure Diagnostician** - Analyzes test failures
- 🔧 **Auto-Fixer Agent** - Applies automated fixes
- 🧩 **Integration Verifier** - Ensures integration consistency
- 🔒 **QA Quality Guardian** - Enforces quality standards
- 🧰 **Environment Auditor** - Validates testing environment

### From Multi-Agent Orchestrator Spec

- **Memory Loader Agent** - Loads and contextualizes `.memory`
- **Context Analyzer Agent** - Interprets technical and functional purpose
- **Branch Creator Agent** - Automates Git branch management
- **Implementation Agent** - Generates code according to specifications
- **Testing Agent** - Ensures quality with comprehensive tests
- **Memory Updater Agent** - Keeps `.memory` updated and alive
- **Validation Agent** - Verifies final build and integrity
- **Reviewer Agent** - Human control and merge decision

## 🚀 Integration with Cursor

### Command Integration

```bash
# Implement specific task
implement T001
implement T002
implement T015

# With scope specification
implement T001 --scope=fastapi
implement T015 --scope=risk-management
```

### Cursor Rules Integration

Add to `.cursor/rules`:

```markdown
# Project Conductor Integration

- Use `implement T0XX` to trigger complete development lifecycle
- Project Conductor coordinates all existing agent systems
- Automatic quality gates and validation
- Human approval required for merge
```

## 📁 Project Structure

```
.memory/
├── code_review/           # Existing Code Review System
│   ├── agents/           # 7 specialized review agents
│   ├── orchestrator.py   # Code review coordinator
│   └── report_generator.py
├── testing/              # Existing Testing System
│   ├── agents/           # 7 specialized testing agents
│   ├── orchestrator.py   # Testing coordinator
│   └── report_generator.py
├── specs/agents/         # Multi-Agent Orchestrator Specs
│   ├── execution_flow.json
│   └── multi_agent_orchestrator.json
├── project_conductor.py  # Main Project Conductor
└── project_conductor_demo.py
```

## 🧪 Demo

Run the demo to see the Project Conductor in action:

```bash
cd .memory
python project_conductor_demo.py
```

Choose between:

1. **Full Project Conductor demo** - Complete lifecycle simulation
2. **Convenience function demo** - Simple task implementation
3. **System integration demo** - Shows coordination with existing systems

## 🎯 Example Command Flow

```
implement T001

🧬 Phase 1: Memory Analysis and Planning
   📋 Task T001 identified: FastAPI Base Structure
   🔗 Dependencies validated: None (foundation task)
   📁 Files to create: app/main.py, tests/test_main.py

⚙️ Phase 2: Environment Setup
   🌿 Branch created: feature/T001-fastapi-base-structure
   🐍 Python environment verified
   📦 Dependencies installed

⚙️ Phase 3: Implementation
   💻 Code generated: app/main.py with FastAPI app
   🧪 Tests created: tests/test_main.py with health checks
   📚 Documentation updated: README.md

🧪 Phase 4: Code Review
   🧑‍💻 Lead Reviewer: Coordinating review process
   🧠 Architecture Analyst: ✅ FastAPI patterns validated
   🔒 Security Auditor: ✅ No security issues found
   📊 Overall: ✅ Code review passed

🧩 Phase 5: Testing
   🧑‍🔬 Lead Tester: Coordinating test execution
   ⚙️ Test Executor: ✅ All tests passed (11/11)
   🔒 QA Guardian: ✅ Coverage 81% (meets threshold)
   📊 Overall: ✅ Testing passed

🚀 Phase 6: Validation and Quality Gates
   ✅ Code quality: PASSED
   ✅ Test quality: PASSED
   ✅ Coverage quality: PASSED
   🎯 Overall: ✅ READY FOR MERGE

📋 Phase 7: Memory Update
   🧠 Memory bank updated with T001 completion
   📝 Progress tracking updated
   📚 Documentation synchronized

🎉 Phase 8: Final Report
   ✅ T001 implementation completed successfully
   🔄 Ready for human review and merge
   📊 Quality metrics: All gates passed
```

## 🔧 Customization

### Adding New Tasks

1. Add task specification to `.memory/specs/tasks/complete_task_breakdown.json`
2. Define dependencies, inputs, outputs, and success criteria
3. Project Conductor will automatically handle the lifecycle

### Extending Agent Systems

1. Add new agents to existing systems (code_review/ or testing/)
2. Update orchestrator specifications
3. Project Conductor will integrate automatically

### Custom Quality Gates

1. Modify quality gate definitions in orchestrator specs
2. Update validation logic in Project Conductor
3. Add custom checks to existing agents

## 📈 Metrics and Analytics

The Project Conductor tracks:

- **Task Completion Rate**: Percentage of successfully completed tasks
- **Quality Gate Pass Rate**: Percentage of tasks passing all quality gates
- **Average Implementation Time**: Time from start to completion
- **Agent System Utilization**: Usage of code review and testing systems
- **Error Recovery Rate**: Success rate of automatic fixes

## 🤝 Contributing

1. Fork the repository
2. Extend existing agent systems rather than creating new ones
3. Follow the established patterns and conventions
4. Add comprehensive tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Status**: Production Ready  
**Integration**: Reuses existing Code Review and Testing systems
