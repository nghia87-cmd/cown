"""
Job Matching Engine - ML-based job matching algorithm

DEPRECATED: This implementation loops through all jobs in Python.
Use matcher_es.ElasticsearchJobMatcher for production (100x faster).

This file kept for backward compatibility and testing.
"""

from typing import Dict, List, Any, Tuple
from decimal import Decimal
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from apps.jobs.models import Job
from apps.authentication.models import User, CandidateProfile
from .models import JobRecommendation

import warnings


class JobMatcher:
    """
    Match candidates with relevant jobs (Legacy Python-loop version)
    
    PERFORMANCE WARNING: This implementation has O(n) complexity.
    For production with 10,000+ jobs, use matcher_es.ElasticsearchJobMatcher instead.
    """
    
    # Weights for different matching factors
    WEIGHTS = {
        'skills': 0.40,        # 40% weight
        'experience': 0.25,    # 25% weight
        'location': 0.20,      # 20% weight
        'salary': 0.15,        # 15% weight
    }
    
    def __init__(self, user: User):
        self.user = user
        self.profile = None
        
        # Get candidate profile
        try:
            self.profile = user.candidate_profile
        except CandidateProfile.DoesNotExist:
            pass
        
        # Warn if job count is high
        if settings.DEBUG:
            job_count = Job.objects.filter(status='PUBLISHED').count()
            if job_count > 1000:
                warnings.warn(
                    f"JobMatcher is looping through {job_count} jobs. "
                    "Consider using ElasticsearchJobMatcher for better performance.",
                    PerformanceWarning
                )
    
    def find_matches(self, limit: int = 20) -> List[JobRecommendation]:
        """
        Find matching jobs for the user
        
        DEPRECATED: Use matcher_es.find_job_matches_es() instead for production.
        This method loops through all jobs in Python (slow for 1000+ jobs).
        """
        
        if not self.profile:
            return []
        
        # Try to use Elasticsearch if available
        try:
            from .matcher_es import find_job_matches_es
            if hasattr(settings, 'ELASTICSEARCH_DSL') and settings.ELASTICSEARCH_DSL:
                return find_job_matches_es(self.user, limit=limit)
        except (ImportError, AttributeError):
            pass
        
        # Fallback to Python loop (slow)
        # Get active jobs
        jobs = Job.objects.filter(
            status='PUBLISHED',
            expires_at__gt=timezone.now()
        ).select_related('company')
        
        # Calculate match scores
        recommendations = []
        
        for job in jobs:
            # Skip if already recommended
            if JobRecommendation.objects.filter(user=self.user, job=job).exists():
                continue
            
            # Calculate match score
            match_data = self._calculate_match_score(job)
            
            if match_data['match_score'] >= 30:  # Minimum threshold
                recommendation = JobRecommendation(
                    user=self.user,
                    job=job,
                    match_score=match_data['match_score'],
                    skills_match=match_data['skills_match'],
                    experience_match=match_data['experience_match'],
                    location_match=match_data['location_match'],
                    salary_match=match_data['salary_match'],
                    match_details=match_data['details']
                )
                recommendations.append(recommendation)
        
        # Sort by match score
        recommendations.sort(key=lambda x: x.match_score, reverse=True)
        
        # Save top N recommendations
        top_recommendations = recommendations[:limit]
        JobRecommendation.objects.bulk_create(top_recommendations)
        
        return top_recommendations
    
    def _calculate_match_score(self, job: Job) -> Dict[str, Any]:
        """Calculate match score for a job"""
        
        # Skills matching
        skills_score, skills_details = self._match_skills(job)
        
        # Experience matching
        experience_score, experience_details = self._match_experience(job)
        
        # Location matching
        location_score, location_details = self._match_location(job)
        
        # Salary matching
        salary_score, salary_details = self._match_salary(job)
        
        # Calculate weighted total
        total_score = (
            skills_score * self.WEIGHTS['skills'] +
            experience_score * self.WEIGHTS['experience'] +
            location_score * self.WEIGHTS['location'] +
            salary_score * self.WEIGHTS['salary']
        )
        
        # Compile match details
        details = {
            'matched_skills': skills_details.get('matched', []),
            'missing_skills': skills_details.get('missing', []),
            'experience_match': experience_details,
            'location_match': location_details,
            'salary_match': salary_details,
            'match_reasons': self._get_match_reasons(
                skills_score, experience_score, location_score, salary_score
            ),
        }
        
        return {
            'match_score': round(Decimal(total_score), 2),
            'skills_match': round(Decimal(skills_score), 2),
            'experience_match': round(Decimal(experience_score), 2),
            'location_match': round(Decimal(location_score), 2),
            'salary_match': round(Decimal(salary_score), 2),
            'details': details,
        }
    
    def _match_skills(self, job: Job) -> Tuple[float, Dict]:
        """Match skills"""
        
        # Get candidate skills from parsed resume or profile
        candidate_skills = []
        
        # Try to get from latest parsed resume
        parsed_resume = self.user.parsed_resumes.filter(
            status='COMPLETED'
        ).order_by('-created_at').first()
        
        if parsed_resume and parsed_resume.skills:
            candidate_skills = [s.lower() for s in parsed_resume.skills]
        
        # Get job required skills
        job_skills = []
        if job.required_skills:
            job_skills = [s.lower() for s in job.required_skills]
        
        if not job_skills:
            return 50.0, {'matched': [], 'missing': []}  # Neutral score
        
        # Calculate matches
        matched_skills = []
        for skill in job_skills:
            if any(skill in cs for cs in candidate_skills):
                matched_skills.append(skill)
        
        missing_skills = [s for s in job_skills if s not in matched_skills]
        
        # Calculate score
        if len(job_skills) > 0:
            score = (len(matched_skills) / len(job_skills)) * 100
        else:
            score = 50.0
        
        return score, {
            'matched': matched_skills,
            'missing': missing_skills,
        }
    
    def _match_experience(self, job: Job) -> Tuple[float, Dict]:
        """Match experience level"""
        
        candidate_years = self.profile.years_of_experience
        
        # Map experience levels to years
        experience_map = {
            'INTERNSHIP': (0, 0),
            'ENTRY': (0, 2),
            'JUNIOR': (1, 3),
            'MIDDLE': (3, 5),
            'SENIOR': (5, 10),
            'LEAD': (8, 15),
            'EXPERT': (10, 100),
        }
        
        job_min, job_max = experience_map.get(job.experience_level, (0, 0))
        
        # Calculate score
        if candidate_years < job_min:
            # Under-qualified
            diff = job_min - candidate_years
            score = max(0, 100 - (diff * 20))  # Penalize 20 points per year
        elif candidate_years > job_max:
            # Over-qualified
            diff = candidate_years - job_max
            score = max(50, 100 - (diff * 10))  # Smaller penalty
        else:
            # Perfect match
            score = 100.0
        
        details = {
            'candidate_years': candidate_years,
            'required_min': job_min,
            'required_max': job_max,
            'match_type': 'perfect' if job_min <= candidate_years <= job_max else 
                         'under' if candidate_years < job_min else 'over'
        }
        
        return score, details
    
    def _match_location(self, job: Job) -> Tuple[float, Dict]:
        """Match location preferences"""
        
        # Get candidate desired locations
        desired_locations = self.profile.desired_locations or []
        
        if not desired_locations:
            return 50.0, {'match': 'no_preference'}  # Neutral
        
        # Check if job location matches
        job_location = job.location.lower() if job.location else ''
        
        for location in desired_locations:
            if location.lower() in job_location or job_location in location.lower():
                return 100.0, {'match': 'exact', 'location': location}
        
        # Check city match
        job_city = job.city.lower() if job.city else ''
        for location in desired_locations:
            if job_city in location.lower() or location.lower() in job_city:
                return 80.0, {'match': 'city', 'location': location}
        
        # Remote jobs get higher score
        if 'remote' in job_location or job.is_remote:
            return 90.0, {'match': 'remote'}
        
        return 30.0, {'match': 'none'}
    
    def _match_salary(self, job: Job) -> Tuple[float, Dict]:
        """Match salary expectations"""
        
        desired_min = self.profile.desired_salary_min
        desired_max = self.profile.desired_salary_max
        
        if not desired_min and not desired_max:
            return 50.0, {'match': 'no_preference'}  # Neutral
        
        job_min = job.salary_min
        job_max = job.salary_max
        
        if not job_min and not job_max:
            return 50.0, {'match': 'not_specified'}
        
        # Check if salary ranges overlap
        if desired_min and job_max:
            if job_max >= desired_min:
                # Job pays at least the minimum desired
                overlap_percent = min(100, (float(job_max) / float(desired_min)) * 100)
                return min(100, overlap_percent), {'match': 'meets_minimum'}
            else:
                # Job pays less than minimum
                shortfall = float(desired_min - job_max) / float(desired_min) * 100
                score = max(0, 100 - shortfall)
                return score, {'match': 'below_minimum', 'shortfall': shortfall}
        
        if desired_max and job_min:
            if job_min <= desired_max:
                return 80.0, {'match': 'within_range'}
        
        return 50.0, {'match': 'unclear'}
    
    def _get_match_reasons(
        self,
        skills_score: float,
        experience_score: float,
        location_score: float,
        salary_score: float
    ) -> List[str]:
        """Get human-readable match reasons"""
        
        reasons = []
        
        if skills_score >= 70:
            reasons.append("Strong skills match")
        elif skills_score >= 50:
            reasons.append("Moderate skills match")
        
        if experience_score >= 80:
            reasons.append("Perfect experience level")
        elif experience_score >= 60:
            reasons.append("Good experience match")
        
        if location_score >= 80:
            reasons.append("Location matches your preferences")
        
        if salary_score >= 70:
            reasons.append("Salary meets your expectations")
        
        return reasons if reasons else ["General match"]


class CandidateMatcher:
    """Match jobs with relevant candidates"""
    
    def __init__(self, job: Job):
        self.job = job
    
    def find_matches(self, limit: int = 20) -> List:
        """Find matching candidates for the job"""
        
        # Get active candidates
        candidates = User.objects.filter(
            role='CANDIDATE',
            is_active=True
        ).select_related('candidate_profile')
        
        # Use JobMatcher in reverse
        matches = []
        
        for candidate in candidates:
            matcher = JobMatcher(candidate)
            if matcher.profile:
                match_data = matcher._calculate_match_score(self.job)
                
                if match_data['match_score'] >= 40:
                    matches.append({
                        'candidate': candidate,
                        'score': match_data['match_score'],
                        'details': match_data,
                    })
        
        # Sort by score
        matches.sort(key=lambda x: x['score'], reverse=True)
        
        return matches[:limit]
