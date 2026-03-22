# REPO EVOLUTION PIPELINE

## Project Overview
Multi-agent system that scans GitHub repos (mk-knight23) and generates
improved mobile re-implementations on GitLab (mk-knight23-mobile).

## Architecture
- **Orchestrator**: LangGraph StateGraph with supervisor pattern
- **Backend**: FastAPI
- **State**: Supabase (repo manifests, generation logs)
- **Queue**: Redis + BullMQ for repo processing
- **LLM**: Claude Sonnet 4.5 (analysis/codegen) + Haiku 4.5 (scanning/docs)

## Agent Pipeline
1. **Scanner** → reads GitHub repos, extracts manifests
2. **Analyzer** → understands the core idea/purpose
3. **Architect** → selects mobile framework, designs navigation
4. **CodeGen** → scaffolds GitLab repo from templates
5. **CI Builder** → attaches .gitlab-ci.yml
6. **DocWriter** → generates README, ARCHITECTURE.md

## Key Commands
```bash
# Run full pipeline on all repos
python -m api.main scan --all

# Run on single repo
python -m api.main scan --repo tool-37-web

# Start API server
uvicorn api.main:app --reload

# Run upgrade cycle
python -m api.main upgrade --all
```

## Framework Selection Rules
- Portfolio/websites → Expo (React Native)
- Web apps/dashboards → React Native + Navigation
- Games → Flutter + Flame
- Utilities/tools → Ionic/Capacitor

## Quality Gates
Every generated repo MUST pass:
1. Lint check (eslint/dartanalyzer)
2. Type check (tsc/dart analyze)
3. Build succeeds (gradle/xcodebuild)
4. At least one test passes

## Cost Optimization
- Cache manifests in Supabase — only re-analyze when commit SHA changes
- Use Haiku for scanning/docs (10x cheaper than Sonnet)
- Batch similar repos — one architecture decision serves many

## File Conventions
- agents/ → LangGraph agent implementations
- graph/ → StateGraph definition, state schema, supervisor
- templates/ → Mobile project templates (Expo, RN, Flutter)
- api/ → FastAPI endpoints
- scripts/ → CLI utilities
