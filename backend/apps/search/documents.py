"""
Elasticsearch Document Mappings
"""

from django.conf import settings
from django_elasticsearch_dsl import Document, fields
from django_elasticsearch_dsl.registries import registry

from apps.jobs.models import Job
from apps.companies.models import Company


@registry.register_document
class JobDocument(Document):
    """Elasticsearch document for Job model"""
    
    # Company nested object
    company = fields.ObjectField(properties={
        'id': fields.TextField(),
        'name': fields.TextField(
            analyzer='standard',
            fields={
                'raw': fields.KeywordField(),
                'suggest': fields.CompletionField(),
            }
        ),
        'slug': fields.KeywordField(),
        'logo': fields.TextField(),
        'industry': fields.TextField(),
        'location': fields.TextField(),
        'company_size': fields.KeywordField(),
    })
    
    # Job fields with analyzers
    title = fields.TextField(
        analyzer='standard',
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )
    
    slug = fields.KeywordField()
    
    description = fields.TextField(analyzer='standard')
    requirements = fields.TextField(analyzer='standard')
    benefits = fields.TextField(analyzer='standard')
    
    # Skills
    skills = fields.TextField(multi=True)
    
    # Location
    location = fields.TextField(
        fields={
            'raw': fields.KeywordField(),
        }
    )
    city = fields.KeywordField()
    
    # Job details
    job_type = fields.KeywordField()
    experience_level = fields.KeywordField()
    education_level = fields.KeywordField()
    
    # Salary
    salary_min = fields.IntegerField()
    salary_max = fields.IntegerField()
    salary_currency = fields.KeywordField()
    
    # Categories
    category = fields.TextField(
        fields={
            'raw': fields.KeywordField(),
        }
    )
    
    # Status
    status = fields.KeywordField()
    is_featured = fields.BooleanField()
    is_urgent = fields.BooleanField()
    
    # Timestamps
    posted_at = fields.DateField()
    expires_at = fields.DateField()
    updated_at = fields.DateField()
    
    # Stats for ranking
    views_count = fields.IntegerField()
    applications_count = fields.IntegerField()
    
    class Index:
        name = 'jobs'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
            'analysis': {
                'analyzer': {
                    'custom_analyzer': {
                        'type': 'custom',
                        'tokenizer': 'standard',
                        'filter': ['lowercase', 'asciifolding'],
                    }
                }
            }
        }
    
    class Django:
        model = Job
        fields = []
        related_models = [Company]
    
    def get_queryset(self):
        return super().get_queryset().select_related('company').filter(status='PUBLISHED')
    
    def get_instances_from_related(self, related_instance):
        if isinstance(related_instance, Company):
            return related_instance.jobs.all()


@registry.register_document
class CompanyDocument(Document):
    """Elasticsearch document for Company model"""
    
    # Company fields
    name = fields.TextField(
        analyzer='standard',
        fields={
            'raw': fields.KeywordField(),
            'suggest': fields.CompletionField(),
        }
    )
    
    slug = fields.KeywordField()
    
    description = fields.TextField(analyzer='standard')
    
    # Details
    industry = fields.TextField(
        fields={
            'raw': fields.KeywordField(),
        }
    )
    
    company_size = fields.KeywordField()
    founded_year = fields.IntegerField()
    
    # Location
    location = fields.TextField(
        fields={
            'raw': fields.KeywordField(),
        }
    )
    city = fields.KeywordField()
    country = fields.KeywordField()
    
    # Contact
    website = fields.TextField()
    email = fields.TextField()
    
    # Benefits
    benefits = fields.TextField(multi=True)
    
    # Status
    is_verified = fields.BooleanField()
    is_featured = fields.BooleanField()
    
    # Timestamps
    created_at = fields.DateField()
    updated_at = fields.DateField()
    
    # Stats for ranking
    jobs_count = fields.IntegerField()
    followers_count = fields.IntegerField()
    
    class Index:
        name = 'companies'
        settings = {
            'number_of_shards': 1,
            'number_of_replicas': 0,
        }
    
    class Django:
        model = Company
        fields = []
    
    def get_queryset(self):
        return super().get_queryset().filter(is_verified=True)
