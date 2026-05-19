# Skill Registry

**Project**: Buscalibre Web Scraper  
**Generated**: 2026-05-13  
**Scan scope**: User-level (`~/.claude/skills/`) + Project-level (`.agents/skills/`)

---

## User-Level Skills

### SDD (Spec-Driven Development)
Orchestration and implementation skills for structured change management:

- **sdd-init** — Initialize SDD context; detect stack, conventions, testing capabilities
- **sdd-new** — Start new SDD change; run exploration then create proposal
- **sdd-explore** — Explore and investigate an idea or feature before committing
- **sdd-propose** — Create a change proposal with intent, scope, and approach
- **sdd-spec** — Write specifications with requirements and scenarios (RFC 2119)
- **sdd-design** — Create technical design document with architecture decisions
- **sdd-tasks** — Break down a change into an implementation task checklist
- **sdd-apply** — Implement SDD tasks — writes code following specs and design
- **sdd-verify** — Validate that implementation matches specs, design, and tasks
- **sdd-archive** — Archive a completed SDD change — syncs specs and closes the cycle
- **sdd-onboard** — Guided end-to-end walkthrough of the SDD workflow

### Code Quality & Review
- **audit-setup** — Audit the global Claude Code configuration for health
- **judgment-day** — Parallel adversarial review protocol (dual independent judges)
- **skill-creator** — Create, modify, improve, and benchmark custom skills

### Documentation & Planning
- **prd-writer** — Write and organize professional product documentation (PRDs)
- **prd-writer-workspace** — PRD workspace utilities

---

## Project-Level Skills

### Browser Automation
- **browser-use** (`.agents/skills/browser-use/`)
  - Description: Automate browser interactions for web testing, form filling, screenshots, data extraction
  - Triggers: Web navigation, form filling, screenshots, data extraction from web pages
  - Tools: Bash via `browser-use:*`
  - Status: Available

---

## Project Conventions

### Documentation
- **CLAUDE.md** — Project-specific instructions for Claude Code
  - Covers: Development workflow, commands, architecture, code style, anti-detection rules
  - Status: Present and detailed
  - Key constraints: Do not randomize User-Agent, preserve delays, skip anti-detection patterns

### No configuration files detected
- `agents.md` — Not found
- `AGENTS.md` — Not found
- `.cursorrules` — Not found
- `GEMINI.md` — Not found
- `copilot-instructions.md` — Not found

---

## Indexing Notes

1. All SDD skills are user-level and available project-wide
2. browser-use is project-specific (Playwright automation)
3. No project-level custom SDD implementations detected
4. CLAUDE.md is the authoritative project convention document
