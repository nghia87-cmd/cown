"""
Search Views
"""

from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from elasticsearch_dsl import Q as ES_Q, Search

from .models import SearchHistory, SavedSearch
from .documents import JobDocument, CompanyDocument
from .serializers import (
    SearchHistorySerializer,
    SavedSearchSerializer,
    JobSearchSerializer,
    CompanySearchSerializer,
    AutocompleteSerializer,
)


class SearchViewSet(viewsets.ViewSet):
    """Search jobs and companies with Elasticsearch"""
    
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'], url_path='jobs')
    def search_jobs(self, request):
        """Search jobs with filters"""
        
        serializer = JobSearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        # Build Elasticsearch query
        search = Search(index='jobs')
        
        # Full-text search
        if params.get('q'):
            query = params['q']
            search = search.query(
                'multi_match',
                query=query,
                fields=['title^3', 'description^2', 'requirements', 'skills^2', 'company.name^2'],
                type='best_fields',
                fuzziness='AUTO'
            )
        else:
            search = search.query('match_all')
        
        # Filters
        filters = []
        
        if params.get('location'):
            filters.append(ES_Q('match', location=params['location']))
        
        if params.get('city'):
            filters.append(ES_Q('term', city=params['city']))
        
        if params.get('job_type'):
            filters.append(ES_Q('term', job_type=params['job_type']))
        
        if params.get('experience_level'):
            filters.append(ES_Q('term', experience_level=params['experience_level']))
        
        if params.get('education_level'):
            filters.append(ES_Q('term', education_level=params['education_level']))
        
        if params.get('category'):
            filters.append(ES_Q('match', category=params['category']))
        
        if params.get('company_id'):
            filters.append(ES_Q('term', **{'company.id': params['company_id']}))
        
        # Salary range
        if params.get('salary_min'):
            filters.append(ES_Q('range', salary_max={'gte': params['salary_min']}))
        
        if params.get('salary_max'):
            filters.append(ES_Q('range', salary_min={'lte': params['salary_max']}))
        
        # Featured/Urgent
        if params.get('is_featured'):
            filters.append(ES_Q('term', is_featured=True))
        
        if params.get('is_urgent'):
            filters.append(ES_Q('term', is_urgent=True))
        
        # Posted date
        if params.get('posted_days'):
            days_ago = timezone.now() - timedelta(days=params['posted_days'])
            filters.append(ES_Q('range', posted_at={'gte': days_ago}))
        
        # Apply filters
        if filters:
            search = search.filter('bool', must=filters)
        
        # Boost featured/urgent jobs
        search = search.query(
            'function_score',
            query=search.query,
            functions=[
                {'filter': ES_Q('term', is_featured=True), 'weight': 2},
                {'filter': ES_Q('term', is_urgent=True), 'weight': 1.5},
            ],
            score_mode='multiply',
            boost_mode='multiply'
        )
        
        # Sorting
        ordering = params.get('ordering', 'relevance')
        if ordering == 'recent':
            search = search.sort('-posted_at')
        elif ordering == 'salary_high':
            search = search.sort('-salary_max')
        elif ordering == 'salary_low':
            search = search.sort('salary_min')
        # relevance uses default ES scoring
        
        # Pagination
        page = params.get('page', 1)
        page_size = params.get('page_size', 20)
        start = (page - 1) * page_size
        search = search[start:start + page_size]
        
        # Execute search
        response = search.execute()
        
        # Log search history
        if request.user.is_authenticated or request.session.session_key:
            SearchHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=params.get('q', ''),
                search_type='JOB',
                filters={k: v for k, v in params.items() if k != 'q'},
                results_count=response.hits.total.value,
                session_id=request.session.session_key or '',
                ip_address=self.get_client_ip(request)
            )
        
        # Format results
        results = []
        for hit in response:
            results.append({
                'id': hit.meta.id,
                'title': hit.title,
                'slug': hit.slug,
                'company': {
                    'id': hit.company.id,
                    'name': hit.company.name,
                    'slug': hit.company.slug,
                    'logo': hit.company.logo,
                    'location': hit.company.location,
                },
                'location': hit.location,
                'job_type': hit.job_type,
                'experience_level': hit.experience_level,
                'salary_min': hit.salary_min,
                'salary_max': hit.salary_max,
                'salary_currency': hit.salary_currency,
                'is_featured': hit.is_featured,
                'is_urgent': hit.is_urgent,
                'posted_at': hit.posted_at,
                'expires_at': hit.expires_at,
            })
        
        return Response({
            'count': response.hits.total.value,
            'page': page,
            'page_size': page_size,
            'results': results
        })
    
    @action(detail=False, methods=['get'], url_path='companies')
    def search_companies(self, request):
        """Search companies with filters"""
        
        serializer = CompanySearchSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        # Build Elasticsearch query
        search = Search(index='companies')
        
        # Full-text search
        if params.get('q'):
            query = params['q']
            search = search.query(
                'multi_match',
                query=query,
                fields=['name^3', 'description^2', 'industry', 'benefits'],
                type='best_fields',
                fuzziness='AUTO'
            )
        else:
            search = search.query('match_all')
        
        # Filters
        filters = []
        
        if params.get('industry'):
            filters.append(ES_Q('match', industry=params['industry']))
        
        if params.get('company_size'):
            filters.append(ES_Q('term', company_size=params['company_size']))
        
        if params.get('location'):
            filters.append(ES_Q('match', location=params['location']))
        
        if params.get('city'):
            filters.append(ES_Q('term', city=params['city']))
        
        if params.get('is_verified'):
            filters.append(ES_Q('term', is_verified=True))
        
        if params.get('is_featured'):
            filters.append(ES_Q('term', is_featured=True))
        
        # Apply filters
        if filters:
            search = search.filter('bool', must=filters)
        
        # Boost verified/featured companies
        search = search.query(
            'function_score',
            query=search.query,
            functions=[
                {'filter': ES_Q('term', is_verified=True), 'weight': 1.5},
                {'filter': ES_Q('term', is_featured=True), 'weight': 2},
            ],
            score_mode='multiply',
            boost_mode='multiply'
        )
        
        # Sorting
        ordering = params.get('ordering', 'relevance')
        if ordering == 'recent':
            search = search.sort('-created_at')
        elif ordering == 'popular':
            search = search.sort('-jobs_count', '-followers_count')
        
        # Pagination
        page = params.get('page', 1)
        page_size = params.get('page_size', 20)
        start = (page - 1) * page_size
        search = search[start:start + page_size]
        
        # Execute search
        response = search.execute()
        
        # Log search history
        if request.user.is_authenticated or request.session.session_key:
            SearchHistory.objects.create(
                user=request.user if request.user.is_authenticated else None,
                query=params.get('q', ''),
                search_type='COMPANY',
                filters={k: v for k, v in params.items() if k != 'q'},
                results_count=response.hits.total.value,
                session_id=request.session.session_key or '',
                ip_address=self.get_client_ip(request)
            )
        
        # Format results
        results = []
        for hit in response:
            results.append({
                'id': hit.meta.id,
                'name': hit.name,
                'slug': hit.slug,
                'description': hit.description,
                'industry': hit.industry,
                'company_size': hit.company_size,
                'location': hit.location,
                'website': hit.website,
                'is_verified': hit.is_verified,
                'is_featured': hit.is_featured,
                'jobs_count': hit.jobs_count,
            })
        
        return Response({
            'count': response.hits.total.value,
            'page': page,
            'page_size': page_size,
            'results': results
        })
    
    @action(detail=False, methods=['get'], url_path='autocomplete')
    def autocomplete(self, request):
        """Autocomplete suggestions"""
        
        serializer = AutocompleteSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data
        
        query = params['q']
        search_type = params.get('type', 'all')
        limit = params.get('limit', 5)
        
        suggestions = []
        
        # Job suggestions
        if search_type in ['job', 'all']:
            job_search = Search(index='jobs').suggest(
                'job_suggest',
                query,
                completion={
                    'field': 'title.suggest',
                    'size': limit,
                    'fuzzy': {'fuzziness': 'AUTO'}
                }
            )
            job_response = job_search.execute()
            
            for option in job_response.suggest.job_suggest[0].options:
                suggestions.append({
                    'text': option.text,
                    'type': 'job',
                    'score': option._score
                })
        
        # Company suggestions
        if search_type in ['company', 'all']:
            company_search = Search(index='companies').suggest(
                'company_suggest',
                query,
                completion={
                    'field': 'name.suggest',
                    'size': limit,
                    'fuzzy': {'fuzziness': 'AUTO'}
                }
            )
            company_response = company_search.execute()
            
            for option in company_response.suggest.company_suggest[0].options:
                suggestions.append({
                    'text': option.text,
                    'type': 'company',
                    'score': option._score
                })
        
        # Sort by score and limit
        suggestions = sorted(suggestions, key=lambda x: x['score'], reverse=True)[:limit]
        
        return Response({'suggestions': suggestions})
    
    @action(detail=False, methods=['get'], url_path='popular-searches')
    def popular_searches(self, request):
        """Get popular searches"""
        
        # Get top 10 searches from last 30 days
        thirty_days_ago = timezone.now() - timedelta(days=30)
        
        popular = SearchHistory.objects.filter(
            created_at__gte=thirty_days_ago,
            query__isnull=False
        ).exclude(
            query=''
        ).values('query', 'search_type').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return Response({'popular_searches': list(popular)})
    
    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """View search history"""
    
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SearchHistory.objects.filter(user=self.request.user)


class SavedSearchViewSet(viewsets.ModelViewSet):
    """Manage saved searches"""
    
    serializer_class = SavedSearchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

