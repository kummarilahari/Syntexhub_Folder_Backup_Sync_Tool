# Folder Backup / Sync Tool (Python)

A command-line utility that creates timestamped **incremental backups**. It copies only new or changed files, records backup activity in a log, and can optionally create ZIP files and remove older backup folders.

## Requirements
- Python 3.8 or newer
- No external Python packages required

## Project files
- `backup_tool.py` — main command-line application
- `README.md` — setup, commands and testing instructions

## Run on Windows
Open Command Prompt in this project folder.

### 1. Check Python
```bash
python --version
```

### 2. Preview a backup (does not copy anything)
```bash
python backup_tool.py --source "C:\Users\YourName\Documents\TestSource" --destination "D:\MyBackups" --dry-run
```

### 3. Create an incremental backup
```bash
python backup_tool.py --source "C:\Users\YourName\Documents\TestSource" --destination "D:\MyBackups"
```

### 4. Create a ZIP as well
```bash
python backup_tool.py --source "C:\Users\YourName\Documents\TestSource" --destination "D:\MyBackups" --zip
```

### 5. Keep only the latest 3 backup folders
```bash
python backup_tool.py --source "C:\Users\YourName\Documents\TestSource" --destination "D:\MyBackups" --zip --keep 3
```

Replace the example paths with folders that exist on your computer. Create a small test source folder and test destination folder first.

## How incremental backup works
1. The program scans the source folder and calculates a SHA-256 hash for each file.
2. It compares the current file hashes with `.backup_state.json` in the destination.
3. New and changed files are copied into a new timestamped `backup_YYYYMMDD_HHMMSS` folder, keeping their relative folder structure.
4. The state file is updated after copying succeeds.
5. Deleted source files are not automatically deleted from old backups. This is a backup tool, not a two-way sync tool.

## CLI options

| Option | Purpose |
|---|---|
| `--source` | Source folder to back up (required) |
| `--destination` | Backup destination (required) |
| `--dry-run` | Preview files without copying |
| `--zip` | Also create a ZIP archive |
| `--keep N` | Keep only the newest N backup folders; 0 keeps all |
| `--log PATH` | Choose log file path |

## Testing checklist
1. Run with `--dry-run`; confirm it lists files and creates no backup folder.
2. Run normally; confirm files appear under a timestamped backup folder.
3. Run again without changing files; confirm it reports that nothing changed.
4. Add a new file; run again and confirm only that file is copied.
5. Edit an existing file; run again and confirm the changed file is copied.
6. Run with `--zip`; confirm a ZIP archive is created.
7. Run with `--keep 2` after creating several backups; confirm only the newest two backup folders remain.

## Important notes
- Keep the backup destination outside the source folder.
- Do not use your only copy of important files as a test.
- The tool does not delete files from previous backups when they are removed from the source.
- The tool uses file hashes for change detection, which is more reliable than checking timestamps alone.
