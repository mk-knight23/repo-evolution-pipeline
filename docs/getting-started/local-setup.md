# Local Setup

## Prerequisites

- Python 3.10+
- Node.js 18+
- Git

Optional for full pipeline:

- GitHub token
- GitLab token

## Steps

1. Create environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure environment values:

```bash
cp .env.example .env
```

4. Run health checks:

```bash
python -m pipeline health
```

5. Run tests:

```bash
pytest
```
