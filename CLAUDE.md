# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Structure

This repository contains code and prompts for managing projects with the following organization:

- `src/` - All prompts and code should be placed here
- `input/` - Input text files
- `output/` - Generated output files

Note: These directories are not yet created but should be used as the codebase develops.

## Development

This is a Python project. Currently there are no dependencies, build tools, or test frameworks configured.

The `main.py` file in the root is a PyCharm boilerplate and should likely be removed or replaced as actual project code is added to `src/`.

## Jira Integration

This repository is focused on managing the **Climate** project on Jira.

- **Project Key**: `CLIM`
- **Project Name**: Climate
- **Lead**: Stian Sandvold

### Common Jira Commands

The repository includes a `/jira` command with Atlassian CLI (acli) reference. Key commands for the CLIM project:

```bash
# List Climate project issues
acli jira workitem search --jql "project = CLIM ORDER BY updated DESC" --limit 20

# View a specific issue
acli jira workitem view CLIM-123

# Create a new task
acli jira workitem create --project CLIM --type Task --summary "Task summary" --description "Details"

# Add a comment to an issue
acli jira workitem comment create --key "CLIM-123" --body "Your comment"
```

See `.claude/commands/jira.md` for complete reference.

## Git Commit Guidelines

When creating commits, do not add Claude Code attribution or co-author information to commit messages.