# Windows Setup Guide

## Problem

The `make` command is not available on Windows by default, causing the error:

```
make: The term 'make' is not recognized as a name of a cmdlet, function, script file, or executable program.
```

## Solution

Use the provided PowerShell or batch scripts instead of `make` commands.

## Quick Reference

| Make Command      | PowerShell             | Batch File             |
| ----------------- | ---------------------- | ---------------------- |
| `make help`       | `.\run.ps1 help`       | `.\run.bat help`       |
| `make install`    | `.\run.ps1 install`    | `.\run.bat install`    |
| `make dev`        | `.\run.ps1 dev`        | `.\run.bat dev`        |
| `make test`       | `.\run.ps1 test`       | `.\run.bat test`       |
| `make format`     | `.\run.ps1 format`     | `.\run.bat format`     |
| `make lint`       | `.\run.ps1 lint`       | `.\run.bat lint`       |
| `make clean`      | `.\run.ps1 clean`      | `.\run.bat clean`      |
| `make db-init`    | `.\run.ps1 db-init`    | `.\run.bat db-init`    |
| `make db-migrate` | `.\run.ps1 db-migrate` | `.\run.bat db-migrate` |
| `make setup`      | `.\run.ps1 setup`      | `.\run.bat setup`      |
| `make run`        | `.\run.ps1 run`        | `.\run.bat run`        |
| `make run-prod`   | `.\run.ps1 run-prod`   | `.\run.bat run-prod`   |

## Special Commands

### Database Revision (Create Migration)

**Make:**

```bash
make db-revision msg="description"
```

**PowerShell:**

```powershell
.\run.ps1 db-revision "description"
```

**Batch:**

```cmd
.\run.bat db-revision "description"
```

## Recommendations

1. **Use PowerShell** (`.\run.ps1`) - Better error handling and colored output
2. **Use Batch** (`.\run.bat`) - If you prefer traditional Windows commands

## Alternative Solutions

If you want to use `make` directly:

1. **Install via Chocolatey:**

   ```powershell
   choco install make
   ```

2. **Install via Scoop:**

   ```powershell
   scoop install make
   ```

3. **Use WSL (Windows Subsystem for Linux):**
   ```powershell
   wsl
   make help
   ```

## Examples

```powershell
# Show all available commands
.\run.ps1 help

# Install dependencies
.\run.ps1 install

# Initialize database
.\run.ps1 db-init

# Run development server
.\run.ps1 run
```

## Notes

- All scripts use `uv run` for Python commands (as per project requirements)
- PowerShell script provides colored output and better error handling
- Batch file is provided for users who prefer traditional Windows commands
- Both scripts provide the exact same functionality as the Makefile
