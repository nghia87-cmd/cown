"""
Celery Tasks for Resume Parser (Optional - for async processing)
"""

from celery import shared_task
from .models import ParsedResume
from .parser import ResumeParser


@shared_task
def parse_resume_task(parsed_resume_id: str):
    """Async task to parse resume"""
    
    try:
        parsed_resume = ParsedResume.objects.get(id=parsed_resume_id)
        parser = ResumeParser(parsed_resume)
        parser.parse()
        return f"Successfully parsed resume {parsed_resume_id}"
    except ParsedResume.DoesNotExist:
        return f"ParsedResume {parsed_resume_id} not found"
    except Exception as e:
        return f"Error parsing resume {parsed_resume_id}: {str(e)}"
