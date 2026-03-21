# Contributing

Thanks for your interest in contributing to Auto Data Analyst Agent.

## How to Contribute

- Fork this repository and create a feature branch from `main`.
- Keep changes focused and small; one concern per pull request.
- Add or update documentation when behavior changes.
- Run the app locally and verify your change before opening a PR.

## Local Development

```bash
pip install -r requirements.txt
python main.py
```

Service default URL: `http://127.0.0.1:8000`

## Pull Request Checklist

- [ ] Code runs locally without errors
- [ ] README or docs updated if needed
- [ ] No secrets committed (`.env`, API keys, credentials)
- [ ] Clear PR title and description

## Commit Message Style

Use concise, imperative messages, for example:

- `feat: add demo dataset download endpoint`
- `fix: handle empty numeric columns in histogram plotting`
- `docs: clarify Docker startup steps`

## Reporting Issues

When opening an issue, please include:

- Expected behavior
- Actual behavior
- Steps to reproduce
- Environment details (OS, Python version)

