"""
Tests for Async Elasticsearch Indexing Tasks
"""
import pytest
from unittest.mock import patch, MagicMock
from apps.search.tasks import (
    index_job_task,
    delete_job_index_task,
    index_company_task,
    delete_company_index_task,
    bulk_reindex_jobs,
    bulk_reindex_companies,
)


@pytest.mark.django_db
class TestAsyncIndexingTasks:
    """Test async Elasticsearch indexing tasks"""
    
    def test_index_job_task_not_found(self):
        """Test indexing non-existent job"""
        import uuid
        fake_id = uuid.uuid4()
        
        result = index_job_task(fake_id)
        
        assert result['status'] == 'not_found'
        assert result['job_id'] == fake_id
    
    def test_bulk_reindex_jobs_no_jobs(self):
        """Test bulk reindexing with no jobs"""
        with patch('apps.search.tasks.registry.update') as mock_update:
            result = bulk_reindex_jobs()
            
            assert result['status'] == 'completed'
            assert result['total'] == 0
            assert result['success'] == 0
            assert result['failed'] == 0
            mock_update.assert_not_called()
    
    def test_bulk_reindex_companies_no_companies(self):
        """Test bulk reindexing with no companies"""
        with patch('apps.search.tasks.registry.update') as mock_update:
            result = bulk_reindex_companies()
            
            assert result['status'] == 'completed'
            assert result['total'] == 0
            assert result['success'] == 0
            assert result['failed'] == 0
            mock_update.assert_not_called()
