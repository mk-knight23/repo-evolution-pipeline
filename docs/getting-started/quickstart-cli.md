# Quickstart CLI

## Batch Run

```bash
python -m pipeline run --manifests data/manifests.example.json --batch-size 5 --max-concurrent 3
```

## Single Repository Run

```bash
python -m pipeline run-single --repo owner/repo-name --category webapp
```

## Quality Check Existing Output

```bash
python -m pipeline quality --files-dir ./output
```

## Health

```bash
python -m pipeline health
```

## Version

```bash
python -m pipeline version
```
