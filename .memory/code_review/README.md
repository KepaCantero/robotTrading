# AlgoTrading Code Review System

A comprehensive code review system with specialized agents that analyze code from multiple expert perspectives and generate actionable reports.

## 🎯 Purpose

When you write **"code review [diff | file | PR]"**, this system triggers a coordinated group of specialized agents that analyze, evaluate, and validate the provided code from multiple expert perspectives.

Each agent reads `.memory`, understands the global project context (architecture, conventions, tasks, dependencies, technical stack), and contributes structured feedback. When done, they synthesize a unified Code Review Report.

## 🧩 Agent Roles

### 🧑‍💻 Lead Reviewer

- Reads `.memory` and understands current project phase and objectives
- Splits the review across specialized agents
- Ensures each agent follows consistent project standards
- Merges feedback into a coherent and actionable report

### 🧠 Architecture Analyst

- Checks if the new code aligns with the system architecture and domain boundaries
- Detects violations of DDD principles, layering, and modularity
- Validates consistency with the overall design patterns and `.memory` schema

### 🧮 Algorithm & Logic Expert

- Evaluates algorithmic correctness and efficiency
- Detects suboptimal loops, data structures, or logic flaws
- Suggests modern algo-trading or data processing improvements if relevant

### 🧱 Code Quality Specialist

- Reviews naming, readability, and maintainability
- Detects code smells, duplication, or lack of abstraction
- Recommends refactors consistent with the repo's conventions

### 🧪 Testing Reviewer

- Ensures all public interfaces are covered by unit tests
- Verifies that tests follow the project's structure and philosophy
- Suggests missing edge cases and integration tests

### 🔒 Security & Performance Auditor

- Evaluates security implications, input validation, and external dependencies
- Analyzes potential bottlenecks or memory leaks
- Suggests performance and safety improvements

### ⚙️ CI/CD & Environment Verifier

- Checks that the change won't break pipelines or deployment flow
- Validates environment variables, Docker setup, and AWS/Azure configs
- Recommends adjustments for stable continuous integration

## 🚀 Quick Start

### Basic Usage

```python
from .orchestrator import CodeReviewOrchestrator

# Initialize orchestrator
orchestrator = CodeReviewOrchestrator(
    project_path="/path/to/project",
    memory_bank_path=".memory"
)

# Review a single file
report = await orchestrator.review_file("app/main.py")

# Review a code diff
report = await orchestrator.review_diff(diff_content, commit_hash)

# Review a pull request
report = await orchestrator.review_pr("feature-branch")
```

### Convenience Functions

```python
from .orchestrator import review_file, review_diff, review_pr

# Quick file review
report = await review_file("/path/to/project", "app/main.py")

# Quick diff review
report = await review_diff("/path/to/project", diff_content, commit_hash)

# Quick PR review
report = await review_pr("/path/to/project", "feature-branch")
```

## 📊 Output Format

The system generates comprehensive reports with the following structure:

### Executive Summary

- Overall status (✅ Ready / ⚠️ Needs fixes / ❌ Not mergeable)
- Key metrics (total findings, severity breakdown)
- Key insights and recommendations

### Detailed Findings Table

| Category     | Agent                      | Summary                | Severity    | Recommendation                         |
| ------------ | -------------------------- | ---------------------- | ----------- | -------------------------------------- |
| Architecture | 🧠 Architecture Analyst    | Misaligned data flow   | 🔴 Critical | Introduce interface to decouple layers |
| Testing      | 🧪 Testing Reviewer        | Missing edge case test | 🟠 High     | Add unit test in `test_executor.py`    |
| Code Style   | 🧱 Code Quality Specialist | Inconsistent naming    | 🟢 Low      | Follow `snake_case` per PEP8           |

### Prioritized Recommendations

- Top 10 recommendations sorted by priority
- Affected categories and finding counts
- Actionable next steps

## 🧾 Workflow

1. **Initialization**

   - The system reads `.memory` to load context, architecture, and dependencies
   - Lead Reviewer defines the review scope (e.g., diff, PR, module)

2. **Decomposition**

   - Each agent performs its specialized review independently
   - Agents analyze code from their domain expertise perspective

3. **Synthesis**

   - Lead Reviewer aggregates all insights into a unified report with:
     - ✅ Strengths
     - ⚠️ Issues
     - 💡 Recommendations
     - 🔧 Suggested Fixes (if applicable)

4. **Memory Update**

   - Update `.memory` if review findings affect architecture, conventions, or dependencies

5. **Delivery**
   - Output a **structured Code Review Report**, prioritized by severity and impact

## 🎯 Severity Levels

- **🔴 Critical**: Security vulnerabilities, architectural violations, blocking issues
- **🟠 High**: Performance issues, missing tests, important refactoring needs
- **🟡 Medium**: Code quality improvements, best practices
- **🟢 Low**: Style issues, minor optimizations, suggestions

## 🔧 Integration

### Cursor Integration

Add this to `.cursor/rules` or as a system command:

```bash
# Review current file
code review file

# Review diff
code review diff

# Review PR
code review pr
```

### CI/CD Integration

```yaml
# .github/workflows/code-review.yml
name: Code Review
on: [pull_request]
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run Code Review
        run: python -m .memory.code_review.demo
```

## 📁 Project Structure

```
.memory/code_review/
├── agents/
│   ├── __init__.py
│   ├── base_agent.py           # Base class for all agents
│   ├── lead_reviewer.py        # 🧑‍💻 Lead Reviewer
│   ├── architecture_analyst.py # 🧠 Architecture Analyst
│   ├── algorithm_expert.py     # 🧮 Algorithm Expert
│   ├── code_quality_specialist.py # 🧱 Code Quality Specialist
│   ├── testing_reviewer.py     # 🧪 Testing Reviewer
│   ├── security_auditor.py     # 🔒 Security Auditor
│   └── cicd_verifier.py        # ⚙️ CI/CD Verifier
├── templates/
│   └── review_report.md        # Report template
├── orchestrator.py             # Main orchestrator
├── report_generator.py         # Report generation
├── demo.py                     # Demo script
└── README.md                   # This file
```

## 🧪 Demo

Run the demo to see the system in action:

```bash
cd .memory/code_review
python demo.py
```

Choose between:

1. **Full system demo** - Reviews actual project files
2. **Specific agent demo** - Shows individual agent capabilities

## 🔍 Example Output

```
🚀 AlgoTrading Code Review System Demo
==================================================
📁 Project Path: /Users/kepa.cantero/Projects/algoTrading
🧠 Memory Bank: .memory

🔍 Demo 1: Reviewing app/main.py
------------------------------
✅ Review completed!
📊 Total Findings: 15
🔴 Critical: 0
🟠 High: 2
🟡 Medium: 5
🟢 Low: 8

📋 Executive Summary:
   Status: ⚠️ Requires fixes before merge - High priority issues found
   Key Insights: 3 insights

💡 Top Recommendations:
   1. 🟠 High - Add input validation and sanitization for all user inputs
   2. 🟡 Medium - Use dependency injection to make code more testable
   3. 🟢 Low - Replace magic numbers with named constants
```

## 🎯 Global Verdict

The system provides a clear verdict:

- **✅ Code ready for merge** - No blocking issues
- **⚠️ Requires fixes before merge** - High priority issues found
- **❌ Not mergeable** - Critical issues must be addressed

## 🔧 Customization

### Adding New Agents

1. Inherit from `BaseReviewAgent`
2. Implement the `analyze()` method
3. Add to the orchestrator's agent list
4. Update the `__init__.py` imports

### Custom Report Formats

1. Add new format to `ReportGenerator.report_templates`
2. Implement the format-specific generation method
3. Update the orchestrator to support the new format

## 📈 Metrics and Analytics

The system tracks:

- **Review Duration**: Time taken for complete analysis
- **Files Analyzed**: Number of files processed
- **Lines of Code**: Total LOC analyzed
- **Test Coverage**: Current test coverage percentage
- **Security Score**: Security assessment score (0-100)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your specialized agent or improvement
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

**Version**: 1.0.0  
**Last Updated**: 2025-01-14  
**Status**: Production Ready
