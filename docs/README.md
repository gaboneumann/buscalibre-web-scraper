# Documentation Index

Complete documentation for the Buscalibre Web Scraper project.

## Core Documentation

- **[TECHNICAL.md](TECHNICAL.md)** — Full architecture, anti-detection layers (7 layers), data flow, file structure, configuration reference
  - Pipeline architecture (2-level iteration)
  - Anti-detection systems in detail
  - File structure and test organization
  - Installation and ethical use

- **[MIGRATION.md](MIGRATION.md)** — ETL Pipeline Architecture Refactor guide
  - Overview of modular refactoring (Phases 1-6)
  - How to upgrade from monolithic to modular design
  - Custom configuration and download strategies
  - Multi-target scraping examples
  - Troubleshooting

- **[PHASE_1_TASKS.md](PHASE_1_TASKS.md)** — Phase 1: Smart Retry Implementation tasks
  - 9 implementation tasks (1.1-1.9)
  - Exponential backoff formulas
  - PRODUCT_PER_PAGE adaptive logic
  - Manual validation checklist (no unit tests)
  - Acceptance criteria

## Quick Links

### For New Users
Start with [TECHNICAL.md](TECHNICAL.md) to understand the architecture, then [MIGRATION.md](MIGRATION.md) for upgrade paths.

### For Developers
- **Architecture decisions**: [TECHNICAL.md — Anti-Detection Systems](TECHNICAL.md#anti-detection-systems-7-layers)
- **Refactoring phases**: [MIGRATION.md — Overview](MIGRATION.md#overview)
- **Phase 1 implementation**: [PHASE_1_TASKS.md](PHASE_1_TASKS.md)

### For Configuration
See [TECHNICAL.md — Configuration Reference](TECHNICAL.md#configuration-reference) for all settings.

## Project Constraints

**Non-negotiable anti-detection constraints** (from TECHNICAL.md):
- Session rotation: 2–4 products per session
- Block detection: 3 consecutive 202/405 failures → auto-stop
- Inter-request delay: 8–15 seconds
- Coffee breaks: Every 10–15 products, sleep 150–250 seconds
- User-Agent: Fixed Chrome 120 (do not randomize)

## File Organization

```
docs/
├── README.md              ← You are here
├── TECHNICAL.md           ← Architecture & implementation
├── MIGRATION.md           ← Refactoring phases 1-6
└── PHASE_1_TASKS.md       ← Phase 1 smart retry tasks
```

See [CLAUDE.md](../CLAUDE.md) for project-specific instructions and development workflow.
