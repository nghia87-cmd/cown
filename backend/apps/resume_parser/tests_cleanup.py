"""
Tests for Cleanup Tasks
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from django.utils import timezone
from datetime import timedelta
from apps.resume_parser.tasks_cleanup import (
    cleanup_temp_resume_files,
    cleanup_old_parsed_resumes,
    optimize_resume_storage,
)


class TestCleanupTasks:
    """Test resume parser cleanup tasks"""
    
    def test_cleanup_temp_resume_files(self):
        """Test temp file cleanup - simplified version"""
        # Just test that the function runs without errors
        result = cleanup_temp_resume_files()
        
        assert 'files_deleted' in result
        assert 'size_freed_mb' in result
        assert 'errors' in result
        assert result['files_deleted'] >= 0
        assert result['errors'] >= 0
    
    @pytest.mark.django_db
    def test_cleanup_old_parsed_resumes(self):
        """Test cleanup of old failed parsing records"""
        from apps.resume_parser.models import ParsedResume
        from apps.authentication.models import User
        from django.core.files.uploadedfile import SimpleUploadedFile
        
        # Create test user
        user = User.objects.create_user(
            email='candidate@test.com',
            password='test123',
            role='CANDIDATE'
        )
        
        # Create dummy file
        dummy_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        
        # Create old failed resume
        old_failed = ParsedResume.objects.create(
            user=user,
            file=dummy_file,
            file_name='test.pdf',
            file_size=12,
            status='FAILED',
            error_message='Test error'
        )
        # Manually set old created_at
        old_failed.created_at = timezone.now() - timedelta(days=40)
        old_failed.save()
        
        # Create recent failed resume (should not be deleted)
        recent_failed = ParsedResume.objects.create(
            user=user,
            file=SimpleUploadedFile("test2.pdf", b"file_content2", content_type="application/pdf"),
            file_name='test2.pdf',
            file_size=13,
            status='FAILED',
            error_message='Recent error'
        )
        
        # Create old completed resume (should not be deleted)
        old_completed = ParsedResume.objects.create(
            user=user,
            file=SimpleUploadedFile("test3.pdf", b"file_content3", content_type="application/pdf"),
            file_name='test3.pdf',
            file_size=13,
            status='COMPLETED'
        )
        old_completed.created_at = timezone.now() - timedelta(days=40)
        old_completed.save()
        
        result = cleanup_old_parsed_resumes()
        
        assert result['deleted_count'] == 1
        assert not ParsedResume.objects.filter(id=old_failed.id).exists()
        assert ParsedResume.objects.filter(id=recent_failed.id).exists()
        assert ParsedResume.objects.filter(id=old_completed.id).exists()
    
    @pytest.mark.django_db
    def test_optimize_resume_storage_no_files(self):
        """Test optimize storage when no old resumes exist"""
        result = optimize_resume_storage()
        
        assert result['compressed_count'] == 0
        assert result['space_saved_mb'] == 0
    
    def test_cleanup_temp_files_no_directory(self):
        """Test cleanup when temp directory doesn't exist"""
        with patch('apps.resume_parser.tasks_cleanup.settings') as mock_settings:
            mock_settings.BASE_DIR = '/nonexistent/path'
            mock_settings.MEDIA_ROOT = '/nonexistent/media'
            
            # Should not raise error
            result = cleanup_temp_resume_files()
            
            assert result['files_deleted'] == 0
            assert result['errors'] == 0
    
    @pytest.mark.django_db
    def test_cleanup_old_resumes_empty_database(self):
        """Test cleanup when no old resumes exist"""
        result = cleanup_old_parsed_resumes()
        
        assert result['deleted_count'] == 0
        assert 'cutoff_date' in result
