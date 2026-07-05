# Contributing Guide - Amica Project

Amica is a women’s safety and security application developed as a team project. This guide explains how developers should work with branches, issues, commits, pull requests, and CI/CD.

## Branch Strategy

We use the following branch structure:

- `main`  
  Stable final branch. Only demo-ready or release-ready code should be merged here.

- `dev`  
  Main development integration branch. All completed features should be merged into `dev` through pull requests.

- `feature/*`  
  For new features.

- `bugfix/*`  
  For fixing bugs.

- `docs/*`  
  For documentation updates.

- `ci/*`  
  For GitHub Actions, CI/CD, or workflow changes.

- `refactor/*`  
  For code cleanup without changing app behavior.

Do not push directly to `main`.  
Do not push directly to `dev` unless it is a very small documentation change approved by the team.

## Branch Naming Convention

Use this format:

```text
<type>/<issue-number>-short-description
```
