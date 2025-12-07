"""
Recommendations Views
"""

from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import JobRecommendation, CandidateRecommendation, RecommendationFeedback
from .serializers import (
    JobRecommendationSerializer,
    CandidateRecommendationSerializer,
    RecommendationFeedbackSerializer,
    GenerateRecommendationsSerializer,
)
from .matcher import JobMatcher, CandidateMatcher


class JobRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """Job recommendations for candidates"""
    
    serializer_class = JobRecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return JobRecommendation.objects.filter(
            user=self.request.user
        ).select_related('job', 'job__company')
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generate job recommendations"""
        
        serializer = GenerateRecommendationsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        limit = serializer.validated_data.get('limit', 20)
        refresh = serializer.validated_data.get('refresh', False)
        
        # Delete existing if refresh
        if refresh:
            JobRecommendation.objects.filter(user=request.user).delete()
        
        # Generate new recommendations
        matcher = JobMatcher(request.user)
        recommendations = matcher.find_matches(limit=limit)
        
        # Serialize and return
        output_serializer = JobRecommendationSerializer(recommendations, many=True)
        
        return Response({
            'count': len(recommendations),
            'recommendations': output_serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='mark-viewed')
    def mark_viewed(self, request, pk=None):
        """Mark recommendation as viewed"""
        
        recommendation = self.get_object()
        
        if not recommendation.viewed:
            recommendation.viewed = True
            recommendation.viewed_at = timezone.now()
            recommendation.save()
        
        return Response({'status': 'marked as viewed'})
    
    @action(detail=True, methods=['post'], url_path='mark-clicked')
    def mark_clicked(self, request, pk=None):
        """Mark recommendation as clicked"""
        
        recommendation = self.get_object()
        
        if not recommendation.clicked:
            recommendation.clicked = True
            recommendation.clicked_at = timezone.now()
            recommendation.save()
        
        return Response({'status': 'marked as clicked'})
    
    @action(detail=True, methods=['post'], url_path='mark-applied')
    def mark_applied(self, request, pk=None):
        """Mark recommendation as applied"""
        
        recommendation = self.get_object()
        
        if not recommendation.applied:
            recommendation.applied = True
            recommendation.applied_at = timezone.now()
            recommendation.save()
        
        return Response({'status': 'marked as applied'})
    
    @action(detail=True, methods=['post'], url_path='dismiss')
    def dismiss(self, request, pk=None):
        """Dismiss recommendation"""
        
        recommendation = self.get_object()
        
        recommendation.dismissed = True
        recommendation.dismissed_at = timezone.now()
        recommendation.save()
        
        return Response({'status': 'dismissed'})
    
    @action(detail=True, methods=['post'], url_path='feedback')
    def feedback(self, request, pk=None):
        """Provide feedback on recommendation"""
        
        recommendation = self.get_object()
        
        rating = request.data.get('rating')
        if rating:
            try:
                rating = int(rating)
                if 1 <= rating <= 5:
                    recommendation.feedback_rating = rating
                    recommendation.save()
                else:
                    return Response(
                        {'error': 'Rating must be between 1 and 5'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except ValueError:
                return Response(
                    {'error': 'Invalid rating value'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response({'status': 'feedback recorded'})
    
    @action(detail=False, methods=['get'], url_path='top-matches')
    def top_matches(self, request):
        """Get top matching jobs"""
        
        top_recommendations = self.get_queryset().filter(
            dismissed=False
        ).order_by('-match_score')[:10]
        
        serializer = JobRecommendationSerializer(top_recommendations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'], url_path='new')
    def new_recommendations(self, request):
        """Get new (unviewed) recommendations"""
        
        new_recs = self.get_queryset().filter(
            viewed=False,
            dismissed=False
        ).order_by('-match_score')
        
        serializer = JobRecommendationSerializer(new_recs, many=True)
        return Response(serializer.data)


class CandidateRecommendationViewSet(viewsets.ReadOnlyModelViewSet):
    """Candidate recommendations for employers"""
    
    serializer_class = CandidateRecommendationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only show recommendations for jobs owned by user's company
        return CandidateRecommendation.objects.filter(
            job__company__members__user=self.request.user
        ).select_related('candidate', 'job')
    
    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generate candidate recommendations for a job"""
        
        job_id = request.data.get('job_id')
        if not job_id:
            return Response(
                {'error': 'job_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.jobs.models import Job
        
        try:
            job = Job.objects.get(id=job_id)
        except Job.DoesNotExist:
            return Response(
                {'error': 'Job not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check permission
        if not job.company.members.filter(user=request.user).exists():
            return Response(
                {'error': 'You do not have permission to generate recommendations for this job'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Generate recommendations
        matcher = CandidateMatcher(job)
        matches = matcher.find_matches(limit=20)
        
        # Save recommendations
        recommendations = []
        for match in matches:
            rec, created = CandidateRecommendation.objects.update_or_create(
                job=job,
                candidate=match['candidate'],
                defaults={
                    'match_score': match['score'],
                    'skills_match': match['details']['skills_match'],
                    'experience_match': match['details']['experience_match'],
                    'match_details': match['details']['details'],
                }
            )
            recommendations.append(rec)
        
        serializer = CandidateRecommendationSerializer(recommendations, many=True)
        
        return Response({
            'count': len(recommendations),
            'recommendations': serializer.data
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'], url_path='mark-viewed')
    def mark_viewed(self, request, pk=None):
        """Mark candidate recommendation as viewed"""
        
        recommendation = self.get_object()
        
        if not recommendation.viewed:
            recommendation.viewed = True
            recommendation.viewed_at = timezone.now()
            recommendation.save()
        
        return Response({'status': 'marked as viewed'})
    
    @action(detail=True, methods=['post'], url_path='shortlist')
    def shortlist(self, request, pk=None):
        """Shortlist a candidate"""
        
        recommendation = self.get_object()
        
        recommendation.shortlisted = True
        recommendation.shortlisted_at = timezone.now()
        recommendation.save()
        
        return Response({'status': 'shortlisted'})


class RecommendationFeedbackViewSet(viewsets.ModelViewSet):
    """Recommendation feedback"""
    
    serializer_class = RecommendationFeedbackSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return RecommendationFeedback.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

