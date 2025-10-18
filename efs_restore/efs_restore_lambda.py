import glob
import logging
import os
import shutil
import time
from pathlib import Path

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log_progress(message, extra=None):
    """Log progress with optional extra data"""
    if extra:
        logger.info(message, extra={'extra': extra})
    else:
        logger.info(message)


def find_restore_directories(pattern):
    """Find directories matching the restore pattern"""
    try:
        efs_root = Path('/mnt/efs')
        if not efs_root.exists():
            raise Exception("EFS root directory /mnt/efs does not exist")

        # Convert glob pattern to search pattern
        search_pattern = str(efs_root / pattern)
        matching_dirs = glob.glob(search_pattern)

        # Filter to only include directories
        restore_dirs = [d for d in matching_dirs if os.path.isdir(d)]

        log_progress(
            f"Found {len(restore_dirs)} directories matching pattern "
            f"'{pattern}'",
            {'pattern': pattern, 'directories': restore_dirs}
        )

        return restore_dirs

    except Exception as e:
        log_progress(f"Error finding restore directories: {str(e)}",
                     {'error': str(e)})
        raise


def check_for_conflicts(source_dir, target_root):
    """Check if moving files would create conflicts"""
    conflicts = []
    source_path = Path(source_dir)
    target_path = Path(target_root)

    try:
        for item in source_path.rglob('*'):
            if item.is_file() or item.is_dir():
                relative_path = item.relative_to(source_path)
                target_item = target_path / relative_path

                if target_item.exists():
                    conflicts.append(str(relative_path))

        if conflicts:
            log_progress(f"Found {len(conflicts)} conflicts",
                         {'conflicts': conflicts})

        return conflicts

    except Exception as e:
        log_progress(f"Error checking for conflicts: {str(e)}",
                     {'error': str(e)})
        raise


def move_contents(source_dir, target_root):
    """Move all contents from source directory to target root"""
    try:
        source_path = Path(source_dir)
        target_path = Path(target_root)

        moved_items = []
        failed_items = []

        # Get all items in source directory
        items = list(source_path.iterdir())
        total_items = len(items)

        log_progress(
            f"Starting to move {total_items} items from {source_dir} "
            f"to {target_root}"
        )

        for i, item in enumerate(items, 1):
            try:
                target_item = target_path / item.name

                # Use shutil.move for atomic move operation
                shutil.move(str(item), str(target_item))
                moved_items.append(item.name)

                # Log progress every 10 items
                if i % 10 == 0 or i == total_items:
                    log_progress(
                        f"Progress: {i}/{total_items} items moved",
                        {
                            'moved': len(moved_items),
                            'failed': len(failed_items)
                        }
                    )

            except Exception as e:
                failed_items.append({'item': item.name, 'error': str(e)})
                log_progress(
                    f"Failed to move {item.name}: {str(e)}",
                    {'item': item.name, 'error': str(e)}
                )

        log_progress(
            "Move operation completed",
            {
                'total_items': total_items,
                'moved': len(moved_items),
                'failed': len(failed_items)
            }
        )

        if failed_items:
            raise Exception(
                f"Failed to move {len(failed_items)} items: {failed_items}"
            )

        return moved_items

    except Exception as e:
        log_progress(f"Error moving contents: {str(e)}", {'error': str(e)})
        raise


def cleanup_empty_directory(directory):
    """Remove the empty restore directory"""
    try:
        source_path = Path(directory)

        # Verify directory is empty
        if any(source_path.iterdir()):
            raise Exception(
                f"Directory {directory} is not empty, cannot remove"
            )

        source_path.rmdir()
        log_progress(f"Successfully removed empty directory: {directory}")

    except Exception as e:
        log_progress(
            f"Error removing directory {directory}: {str(e)}",
            {'error': str(e)}
        )
        raise


def handle(event, context):
    start_time = time.time()

    try:
        log_progress(
            "Starting EFS restore directory move operation",
            {
                'event': event,
                'context': {
                    'function_name': context.function_name,
                    'function_version': context.function_version,
                    'invoked_function_arn': context.invoked_function_arn,
                    'memory_limit_in_mb': context.memory_limit_in_mb,
                    'remaining_time_in_millis': (
                        context.get_remaining_time_in_millis()
                    )
                }
            }
        )

        # Get restore directory pattern from environment
        restore_pattern = os.environ.get(
            'RESTORE_DIRECTORY_PATTERN', 'aws-backup-restore_*'
        )
        log_progress(f"Using restore directory pattern: {restore_pattern}")

        # Find restore directories
        restore_dirs = find_restore_directories(restore_pattern)

        if not restore_dirs:
            error_msg = (
                f"No directories found matching pattern '{restore_pattern}' "
                f"in /mnt/efs"
            )
            log_progress(error_msg)
            raise Exception(error_msg)

        if len(restore_dirs) > 1:
            error_msg = (
                f"Multiple restore directories found: {restore_dirs}. "
                f"Only one restore directory is allowed."
            )
            log_progress(error_msg)
            raise Exception(error_msg)

        restore_dir = restore_dirs[0]
        log_progress(f"Processing restore directory: {restore_dir}")

        # Check for conflicts
        conflicts = check_for_conflicts(restore_dir, '/mnt/efs')
        if conflicts:
            error_msg = (
                f"Conflicts detected. The following files/directories "
                f"already exist in /mnt/efs: {conflicts}"
            )
            log_progress(error_msg)
            raise Exception(error_msg)

        # Move contents
        moved_items = move_contents(restore_dir, '/mnt/efs')

        # Clean up empty directory
        cleanup_empty_directory(restore_dir)

        execution_time = time.time() - start_time

        result = {
            'statusCode': 200,
            'body': {
                'message': (
                    'Successfully moved restore directory contents to EFS root'
                ),
                'restore_directory': restore_dir,
                'moved_items_count': len(moved_items),
                'execution_time_seconds': round(execution_time, 2),
                'moved_items': moved_items
            }
        }

        log_progress(
            "EFS restore directory move operation completed successfully",
            {'result': result['body']}
        )

        return result

    except Exception as e:
        execution_time = time.time() - start_time
        error_msg = f"EFS restore directory move operation failed: {str(e)}"

        log_progress(
            error_msg,
            {
                'error': str(e),
                'execution_time_seconds': round(execution_time, 2)
            }
        )

        return {
            'statusCode': 500,
            'body': {
                'message': error_msg,
                'error': str(e),
                'execution_time_seconds': round(execution_time, 2)
            }
        }
