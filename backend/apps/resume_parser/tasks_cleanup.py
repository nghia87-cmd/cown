"""
Cleanup temporary files from resume parsing operations
Runs as periodic Celery task
"""

from celery import shared_task
import os
import time
import logging
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task
def cleanup_temp_resume_files():
    """
    Clean up temporary files created during resume parsing
    Removes files older than 1 hour from /tmp directory
    
    Returns:
        dict: Cleanup statistics
    """
    temp_dirs = [
        '/tmp',
        os.path.join(settings.BASE_DIR, 'tmp'),
        os.path.join(settings.MEDIA_ROOT, 'tmp')
    ]
    
    total_deleted = 0
    total_size_freed = 0
    errors = 0
    
    # File patterns from resume parsing
    patterns = [
        '*.pdf_page_*.png',  # pdf2image temp files
        'resume_*.tmp',       # Temporary resume files
        'parsed_*.json',      # Temporary parsed data
        'tesseract_*',        # OCR temp files
    ]
    
    for temp_dir in temp_dirs:
        if not os.path.exists(temp_dir):
            continue
        
        try:
            for pattern in patterns:
                for file_path in Path(temp_dir).rglob(pattern):
                    try:
                        # Check if file is older than 1 hour
                        if time.time() - file_path.stat().st_mtime > 3600:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            total_deleted += 1
                            total_size_freed += file_size
                            logger.debug(f"Deleted temp file: {file_path}")
                    except Exception as e:
                        errors += 1
                        logger.error(f"Error deleting {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error accessing {temp_dir}: {e}")
    
    result = {
        'files_deleted': total_deleted,
        'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
        'errors': errors
    }
    
    logger.info(f"Temp file cleanup completed: {result}")
    return result


@shared_task
def cleanup_old_parsed_resumes():
    """
    Archive or delete very old parsed resumes from database
    Removes FAILED parsing records older than 30 days
    
    Returns:
        dict: Cleanup statistics
    """
    from apps.resume_parser.models import ParsedResume
    from django.utils import timezone
    from datetime import timedelta
    
    # Delete failed parsing attempts older than 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    
    failed_resumes = ParsedResume.objects.filter(
        status='FAILED',
        created_at__lt=cutoff_date
    )
    
    count = failed_resumes.count()
    failed_resumes.delete()
    
    logger.info(f"Deleted {count} old failed parsed resumes")
    
    return {
        'deleted_count': count,
        'cutoff_date': cutoff_date.isoformat()
    }


@shared_task
def optimize_resume_storage():
    """
    Compress and optimize stored resume files
    Move old resumes to cold storage (S3 Glacier)
    
    Returns:
        dict: Optimization statistics
    """
    from apps.resume_parser.models import ParsedResume
    from django.utils import timezone
    from datetime import timedelta
    import gzip
    import shutil
    
    # Process resumes older than 90 days
    cutoff_date = timezone.now() - timedelta(days=90)
    
    old_resumes = ParsedResume.objects.filter(
        created_at__lt=cutoff_date,
        status='COMPLETED'
    ).exclude(
        file__isnull=True
    )[:100]  # Process in batches
    
    compressed_count = 0
    space_saved = 0
    
    for resume in old_resumes:
        try:
            if resume.file and os.path.exists(resume.file.path):
                original_size = os.path.getsize(resume.file.path)
                
                # Check if already compressed
                if not resume.file.path.endswith('.gz'):
                    # Compress file
                    gz_path = resume.file.path + '.gz'
                    with open(resume.file.path, 'rb') as f_in:
                        with gzip.open(gz_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                    
                    compressed_size = os.path.getsize(gz_path)
                    space_saved += (original_size - compressed_size)
                    
                    # Remove original
                    os.remove(resume.file.path)
                    
                    # Update file path in database
                    resume.file.name = resume.file.name + '.gz'
                    resume.save(update_fields=['file'])
                    
                    compressed_count += 1
        except Exception as e:
            logger.error(f"Error compressing resume {resume.id}: {e}")
    
    result = {
        'compressed_count': compressed_count,
        'space_saved_mb': round(space_saved / (1024 * 1024), 2)
    }
    
    logger.info(f"Resume storage optimization completed: {result}")
    return result
