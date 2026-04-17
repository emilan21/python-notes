# Python Project Plan: Terminal Notes / Wiki CLI

## Goal
Build a local CLI app for creating, organizing, searching, and managing markdown-style notes stored on disk.

## Scope
- single-user local tool
- file-based storage first
- plain text or markdown notes with metadata
- CLI-first, no sync or cloud support in the first version

## Suggested Directory Structure
```text
notes-cli-python/
├─ pyproject.toml
├─ README.md
├─ src/
│  └─ notes_cli/
│     ├─ cli/
│     ├─ core/
│     ├─ storage/
│     ├─ output/
│     └─ config.py
├─ tests/
├─ data/notes/
└─ docs/
```

## Needed Features
- create note from title
- generate slug or safe filename
- list notes with sorting/filtering
- show note by id, slug, or title
- edit note
- delete or archive note
- tags
- search titles and body text
- config for notes directory and editor

## Nice to Have Features
- wiki-style links and backlinks
- templates for different note types
- daily notes
- export to JSON/CSV/combined markdown
- stats such as note count and tag usage
- lightweight search index
- archive support

## Milestones

### MVP
- new
- list
- show
- delete
- search
- tags

### Second Milestone
- edit via editor integration
- metadata validation
- templates
- backlinks

### Stretch Milestone
- sqlite backend
- terminal UI
- faster indexed search

## Language-Specific Notes
- Use pathlib for file handling.
- Typer or argparse both fit well for the CLI.
- Dataclasses or pydantic models can keep note metadata clean.
- Markdown plus YAML frontmatter is a natural storage format.
