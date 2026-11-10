#!/usr/bin/env python3
"""
Folder Backup / Sync Tool
Creates timestamped incremental backups. Only new or changed files are copied.
No third-party packages are required.
"""
import argparse
import hashlib
import json
import logging
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

MANIFEST_NAME = "backup_manifest.json"
STATE_NAME = ".backup_state.json"


def setup_logging(log_file: Path) -> None:
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler(sys.stdout)],
        force=True,
    )


def file_signature(path: Path) -> dict:
    """Return size, modified time and SHA-256 for reliable change detection."""
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    stat = path.stat()
    return {"size": stat.st_size, "sha256": digest.hexdigest(), "modified": stat.st_mtime}


def load_state(state_file: Path) -> dict:
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        logging.warning("Previous state file could not be read; treating this as a first backup.")
        return {}


def collect_files(source: Path, destination: Path) -> dict:
    result = {}
    for path in source.rglob("*"):
        if not path.is_file():
            continue
        # Avoid backing up the destination if it is inside the source folder.
        try:
            path.relative_to(destination)
            continue
        except ValueError:
            pass
        relative = path.relative_to(source).as_posix()
        result[relative] = file_signature(path)
    return result


def create_backup(source: Path, destination: Path, dry_run: bool = False,
                  make_zip: bool = False, keep: int = 0) -> int:
    source = source.expanduser().resolve()
    destination = destination.expanduser().resolve()

    if not source.exists() or not source.is_dir():
        raise ValueError(f"Source folder does not exist or is not a directory: {source}")
    if source == destination:
        raise ValueError("Source and destination folders must be different.")

    destination.mkdir(parents=True, exist_ok=True) if not dry_run else None
    state_file = destination / STATE_NAME
    previous = load_state(state_file) if not dry_run else {}
    current = collect_files(source, destination)
    changed = [name for name, info in current.items() if previous.get(name, {}).get("sha256") != info["sha256"]]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_folder = destination / f"backup_{timestamp}"

    logging.info("Source: %s", source)
    logging.info("Destination: %s", destination)
    logging.info("Files found: %d | New/changed files: %d", len(current), len(changed))

    if not changed:
        logging.info("Nothing new or changed. Backup not created.")
        return 0

    if dry_run:
        logging.info("DRY RUN: no files will be copied or changed.")
        for name in changed:
            logging.info("Would copy: %s", name)
        return len(changed)

    backup_folder.mkdir(parents=True, exist_ok=False)
    for name in changed:
        source_file = source / Path(name)
        target_file = backup_folder / Path(name)
        target_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, target_file)
        logging.info("Copied: %s", name)

    manifest = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "source": str(source),
        "files_in_this_backup": changed,
        "file_count": len(changed),
    }
    (backup_folder / MANIFEST_NAME).write_text(json.dumps(manifest, indent=4), encoding="utf-8")

    if make_zip:
        zip_path = destination / f"{backup_folder.name}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            for item in backup_folder.rglob("*"):
                if item.is_file():
                    archive.write(item, item.relative_to(backup_folder))
        logging.info("Compressed backup: %s", zip_path)

    # Update state only after the backup files have been copied successfully.
    state_file.write_text(json.dumps(current, indent=4), encoding="utf-8")
    logging.info("Backup completed successfully: %s", backup_folder)

    if keep > 0:
        backups = sorted(
            [p for p in destination.iterdir() if p.is_dir() and p.name.startswith("backup_")],
            key=lambda p: p.name,
            reverse=True,
        )
        for old_backup in backups[keep:]:
            shutil.rmtree(old_backup)
            old_zip = destination / f"{old_backup.name}.zip"
            if old_zip.exists():
                old_zip.unlink()
            logging.info("Removed old backup: %s", old_backup.name)

    return len(changed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create incremental backups of a folder (new and changed files only)."
    )
    parser.add_argument("--source", required=True, help="Folder to back up")
    parser.add_argument("--destination", required=True, help="Folder where backups will be stored")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be copied without copying")
    parser.add_argument("--zip", action="store_true", help="Also create a ZIP archive of this backup")
    parser.add_argument("--keep", type=int, default=0, help="Keep only the newest N backup folders (0 = keep all)")
    parser.add_argument("--log", default="backup_tool.log", help="Log file path (default: backup_tool.log)")
    args = parser.parse_args()

    if args.keep < 0:
        parser.error("--keep must be zero or greater")

    setup_logging(Path(args.log))
    try:
        count = create_backup(
            Path(args.source), Path(args.destination),
            dry_run=args.dry_run, make_zip=args.zip, keep=args.keep
        )
        logging.info("Finished. Files copied: %d", count)
    except (OSError, ValueError) as error:
        logging.error("Backup failed: %s", error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
