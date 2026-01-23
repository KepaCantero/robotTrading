#!/usr/bin/env bash
# Claude Code Script: Enhanced Review with Skills
# Usage: ./review-with-skills.sh <type> <files>

REVIEW_TYPE=${1:-"code"}
FILES=${2:-"src/"}
SKILLS_DIR=".agents/skills"

# Detectar qué skill usar según el tipo
case "$REVIEW_TYPE" in
  ux|ui|design|accessibility)
    SKILL="web-design-guidelines"
    AGENT="code-reviewer"
    ;;
  performance|bundle|optimization)
    SKILL="vercel-react-best-practices"
    AGENT="performance-optimizer"
    ;;
  security|sec)
    AGENT="code-reviewer"
    SKILL=""
    ;;
  architecture|arch)
    AGENT="tech-lead-orchestrator"
    SKILL=""
    ;;
  *)
    AGENT="code-reviewer"
    SKILL=""
    ;;
esac

# Construir el prompt con el skill
if [ -n "$SKILL" ] && [ -f "$SKILLS_DIR/$SKILL/SKILL.md" ]; then
  SKILL_CONTENT=$(cat "$SKILLS_DIR/$SKILL/SKILL.md")
  echo "🎯 Applying skill: $SKILL"
  echo "📋 Agent: $AGENT"
  echo ""
  echo "Ask Claude:"
  echo ""
  echo "Task({ subagent: '$AGENT', prompt: \"
  echo \"@skill: $SKILL
  echo
  echo $SKILL_CONTENT
  echo
  echo Review: $FILES
  echo \"})"
else
  echo "🎯 Agent: $AGENT (no skill)"
  echo ""
  echo "Ask Claude:"
  echo ""
  echo "Task({ subagent: '$AGENT', prompt: 'Review: $FILES' })"
fi
