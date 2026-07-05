# Contributing Guide - Amica Project

Amica is a women's safety and security application developed as a team project. This guide explains how beginner developers should work with branches, issues, commits, pull requests, and CI/CD.

The most important rule is simple:

```text
Do your work in a separate branch, then open a pull request to dev.
```

## Branch Strategy

We use branches to keep production-ready code separate from active development work.

- `main`  
  Production/demo-ready branch. This branch should contain stable code only. Do not push directly to `main`.

- `dev`  
  Main development branch. Completed features are merged into `dev` through pull requests.

- `feature/*`  
  Use for new features.

- `bugfix/*`  
  Use for fixing bugs.

- `docs/*`  
  Use for documentation updates.

- `ci/*`  
  Use for GitHub Actions, CI/CD, or workflow changes.

- `refactor/*`  
  Use for code cleanup that does not change app behavior.

Do not push directly to `main`.  
Do not push directly to `dev` unless it is a very small documentation change approved by the team.

## Branch Naming Convention

Use this format:

```text
<type>/<issue-number>-short-description
```

Examples:

```text
feature/12-plate-ocr-cleaner
feature/18-voice-phrase-matcher
bugfix/21-fix-empty-plate-text
docs/25-update-ai-architecture
ci/30-add-python-tests
refactor/34-clean-decision-engine
```

If there is no issue number yet, create or ask for an issue first. Issues help the team know why a branch exists.

## Beginner Workflow

Follow these steps when starting any task.

1. Make sure you are on `dev`.

```bash
git checkout dev
git pull origin dev
```

2. Create a new branch from `dev`.

```bash
git checkout -b feature/12-plate-ocr-cleaner
```

3. Make your changes.

For example, if you are working on plate OCR text cleaning, edit files inside:

```text
plate_ocr/src/
plate_ocr/tests/
```

4. Check what changed.

```bash
git status
git diff
```

5. Run relevant checks.

```bash
python -m compileall .
pytest
```

If `pytest` is not installed yet, install dependencies first:

```bash
pip install -r requirements.txt
pytest
```

6. Stage and commit your changes.

```bash
git add plate_ocr/src/plate_text_cleaner.py plate_ocr/tests/test_plate_text_cleaner.py
git commit -m "Add plate OCR text cleaner"
```

7. Push your branch.

```bash
git push origin feature/12-plate-ocr-cleaner
```

8. Open a pull request on GitHub.

The pull request should target:

```text
base branch: dev
compare branch: your feature branch
```

## Commit Message Examples

Good commit messages are short and clear.

Good examples:

```text
Add plate OCR text cleaner
Add voice phrase matcher tests
Update AI architecture documentation
Fix unknown vehicle status handling
```

Avoid vague messages:

```text
changes
update
final
fix
my work
```

## Pull Request Guidelines

Before opening a pull request, make sure:

- Your branch is created from the latest `dev`.
- Your pull request targets `dev`, not `main`.
- Your code or documentation matches the issue you are solving.
- You did not commit private files, API keys, tokens, datasets, or personal recordings.
- You ran relevant checks, or you explained why you could not run them.
- Your pull request description explains what changed.

Example pull request summary:

```text
This PR adds a simple plate text cleaning function for OCR output.

Changes:
- Removes spaces and symbols from detected plate text
- Converts plate text to uppercase
- Adds unit tests for common OCR input formats

Checks:
- python -m compileall .
- pytest
```

## Issue Workflow

Each task should have a GitHub issue.

An issue usually includes:

- A clear title
- A short description
- A checklist
- Labels such as `ai`, `documentation`, `testing`, or `priority-high`
- One assignee
- A milestone

Example issue title:

```text
Create voice secret phrase prototype
```

Example checklist:

```text
- [ ] Receive voice transcript text
- [ ] Normalize transcript
- [ ] Match secret phrase
- [ ] Return true or false
- [ ] Add tests for phrase matcher
```

When you open a pull request, link the issue in the PR description:

```text
Closes #12
```

## CI/CD Basics

CI/CD means GitHub automatically checks the project when code is pushed or a pull request is opened.

For this repository, CI may run commands like:

```bash
python -m compileall .
pytest
```

If CI fails:

1. Open the failed GitHub Actions run.
2. Read the error message.
3. Fix the problem in your branch.
4. Commit and push again.

Do not ignore failed CI. Ask the team for help if the error is confusing.

## AI Core Development Notes

This repository contains prototype AI features. Keep code simple and testable.

Main areas:

- `plate_ocr/` for number plate OCR helpers
- `voice_sos/` for secret phrase detection
- `decision_engine/` for SOS trigger decision logic
- `integration_contracts/` for shared mobile/backend schemas
- `docs/` for architecture and flow documentation

When adding AI logic:

- Start with simple placeholder logic.
- Add tests for the logic.
- Do not commit large models or datasets.
- Do not commit real user images, voice recordings, or private data.
- Document assumptions clearly.

## Secrets and Private Data

Never commit:

- API keys
- Firebase credentials
- Private keys
- Access tokens
- Real user location data
- Real voice recordings
- Real number plate images from private users
- Large model files unless the team approves

If you accidentally commit a secret, tell the team immediately. Do not try to hide it with another commit.

## Asking for Help

Ask for help when:

- You are not sure which branch to use.
- You do not understand an issue.
- Tests fail and you cannot understand why.
- You need access to a dataset, API, or Firebase project.
- You are unsure whether a file contains private data.

A good help message includes:

```text
I am working on issue #12.
My branch is feature/12-plate-ocr-cleaner.
I ran pytest and got this error: <paste error here>.
I already tried checking the function input and test case.
```

## Quick Reference

Common commands:

```bash
git checkout dev
git pull origin dev
git checkout -b feature/12-short-description
git status
git add .
git commit -m "Short clear message"
git push origin feature/12-short-description
```

Before requesting review:

```bash
python -m compileall .
pytest
```
