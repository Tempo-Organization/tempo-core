# Cross platform shebang:
shebang := if os() == 'windows' {
  'powershell.exe'
} else {
  '/usr/bin/env pwsh'
}

# Set shell for non-Windows OSs:
set shell := ["powershell", "-c"]

# Set shell for Windows OSs:
set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

# If you have PowerShell Core installed and want to use it,
# use `pwsh.exe` instead of `powershell.exe`


alias list := default

default:
  just --list

setup:
  uv venv
  uv sync

clean:
  if (Test-Path ".venv") { Remove-Item ".venv" -Recurse -Force }
  git clean -d -X --force

commit:
  uv run cz commit

commit_retry:
  uv run cz commit -- --retry

mkdocs_build:
  mkdocs build

mkdocs_serve:
  mkdocs serve

refresh_deps:
  uv lock --upgrade
