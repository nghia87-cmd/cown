"""
LLM CV Analysis Service
ChatGPT/Gemini integration for intelligent resume screening
"""
import hashlib
import json
import time
from decimal import Decimal
from datetime import timedelta
from typing import Optional, Dict, Any
from django.utils import timezone
from django.conf import settings
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)


class LLMAnalysisService:
    """
    AI-powered CV analysis using ChatGPT or Gemini
    """
    
    # Default prompt template
    DEFAULT_SYSTEM_PROMPT = """You are an expert technical recruiter and HR professional with 15+ years of experience. 
Your task is to analyze resumes/CVs against job descriptions and provide detailed, actionable insights.
Be thorough but fair in your assessment. Focus on:
1. Technical skills match
2. Experience relevance and seniority
3. Education fit
4. Red flags or concerns
5. Potential for growth

Provide scores on a 0-100 scale where:
- 90-100: Exceptional candidate, strong hire
- 70-89: Good candidate, proceed to interview
- 50-69: Average candidate, consider if pool is limited
- Below 50: Not recommended for this role"""

    DEFAULT_USER_PROMPT = """Analyze this CV against the job description and provide a detailed assessment.

**Job Title:** {job_title}

**Job Description:**
{job_description}

**Candidate CV:**
{cv_text}

**Required Skills:**
{required_skills}

**Nice-to-Have Skills:**
{preferred_skills}

Provide your analysis in JSON format with the following structure:
{{
    "overall_score": <0-100>,
    "technical_score": <0-100>,
    "experience_score": <0-100>,
    "education_score": <0-100>,
    "culture_fit_score": <0-100>,
    "strengths": ["strength 1", "strength 2", ...],
    "weaknesses": ["weakness 1", "weakness 2", ...],
    "skills_match": {{
        "matched": ["skill 1", "skill 2", ...],
        "missing": ["skill 1", "skill 2", ...],
        "similar": ["python -> java", ...]
    }},
    "experience_match": {{
        "years_required": X,
        "years_candidate": Y,
        "seniority": "junior|mid|senior|lead",
        "relevant_experience": "description"
    }},
    "interview_questions": ["question 1", "question 2", ...] (suggest 5 specific questions),
    "hiring_recommendation": "detailed recommendation text",
    "red_flags": ["flag 1", "flag 2", ...] (if any)
}}"""
    
    def __init__(self, provider: str = 'OPENAI'):
        """
        Initialize LLM service
        
        Args:
            provider: 'OPENAI', 'GEMINI', or 'CLAUDE'
        """
        self.provider = provider
        
        if provider == 'OPENAI':
            api_key = settings.OPENAI_API_KEY if hasattr(settings, 'OPENAI_API_KEY') else None
            if not api_key:
                raise ValueError("OPENAI_API_KEY not configured in settings")
            self.client = OpenAI(api_key=api_key)
            self.model = 'gpt-4o-mini'  # Cost-effective for CV analysis
        elif provider == 'GEMINI':
            # TODO: Implement Gemini client
            raise NotImplementedError("Gemini integration coming soon")
        elif provider == 'CLAUDE':
            # TODO: Implement Claude client
            raise NotImplementedError("Claude integration coming soon")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def analyze_cv(
        self,
        resume_id: str,
        job_id: Optional[str] = None,
        use_cache: bool = True,
        user=None
    ) -> 'CVAnalysis':
        """
        Analyze CV with or without job description
        
        Args:
            resume_id: UUID of ParsedResume
            job_id: UUID of Job (optional)
            use_cache: Check cache before calling LLM
            user: User requesting analysis (for tracking)
        
        Returns:
            CVAnalysis object with results
        """
        from apps.resume_parser.models import ParsedResume
        from apps.resume_parser.models_llm import CVAnalysis, CVAnalysisCache
        from apps.jobs.models import Job
        
        # Get resume
        resume = ParsedResume.objects.get(id=resume_id)
        job = Job.objects.get(id=job_id) if job_id else None
        
        # Check cache
        if use_cache:
            cached = self._get_from_cache(resume, job)
            if cached:
                logger.info(f"Cache hit for CV analysis: {resume_id}")
                cached.record_hit()
                return cached.analysis
        
        # Prepare CV text
        cv_text = self._prepare_cv_text(resume)
        
        # Prepare job details
        if job:
            job_title = job.title
            job_description = job.description
            required_skills = ', '.join([s.name for s in job.required_skills.all()]) if hasattr(job, 'required_skills') else ''
            preferred_skills = ', '.join([s.name for s in job.preferred_skills.all()]) if hasattr(job, 'preferred_skills') else ''
        else:
            # Standalone CV analysis
            job_title = "General Position"
            job_description = "Analyze this CV for general strengths, weaknesses, and market positioning."
            required_skills = ""
            preferred_skills = ""
        
        # Call LLM
        start_time = time.time()
        llm_result = self._call_llm(
            cv_text=cv_text,
            job_title=job_title,
            job_description=job_description,
            required_skills=required_skills,
            preferred_skills=preferred_skills
        )
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Parse response
        analysis_data = self._parse_llm_response(llm_result['response'])
        
        # Create CVAnalysis record
        analysis = CVAnalysis.objects.create(
            resume=resume,
            job=job,
            llm_provider=self.provider,
            model_version=self.model,
            overall_score=analysis_data.get('overall_score'),
            technical_score=analysis_data.get('technical_score'),
            experience_score=analysis_data.get('experience_score'),
            education_score=analysis_data.get('education_score'),
            culture_fit_score=analysis_data.get('culture_fit_score'),
            strengths=analysis_data.get('strengths', []),
            weaknesses=analysis_data.get('weaknesses', []),
            skills_match=analysis_data.get('skills_match', {}),
            experience_match=analysis_data.get('experience_match', {}),
            interview_questions=analysis_data.get('interview_questions', []),
            hiring_recommendation=analysis_data.get('hiring_recommendation', ''),
            red_flags=analysis_data.get('red_flags', []),
            raw_llm_response=llm_result['raw_response'],
            prompt_tokens=llm_result['prompt_tokens'],
            completion_tokens=llm_result['completion_tokens'],
            total_cost_usd=llm_result['cost'],
            analysis_duration_ms=duration_ms,
            created_by=user,
        )
        
        # Cache result
        if use_cache:
            self._save_to_cache(resume, job, analysis)
        
        logger.info(f"CV analysis completed: {resume_id}, Score: {analysis.overall_score}, Cost: ${analysis.total_cost_usd}")
        
        return analysis
    
    def _prepare_cv_text(self, resume: 'ParsedResume') -> str:
        """
        Extract relevant text from ParsedResume
        """
        sections = []
        
        # Basic info
        sections.append(f"Name: {resume.candidate_name or 'N/A'}")
        sections.append(f"Email: {resume.email or 'N/A'}")
        sections.append(f"Phone: {resume.phone or 'N/A'}")
        
        # Skills
        if resume.skills:
            skills_str = ', '.join(resume.skills) if isinstance(resume.skills, list) else resume.skills
            sections.append(f"\nSkills: {skills_str}")
        
        # Experience
        if resume.experience:
            sections.append(f"\nExperience:\n{resume.experience}")
        
        # Education
        if resume.education:
            sections.append(f"\nEducation:\n{resume.education}")
        
        # Summary
        if resume.summary:
            sections.append(f"\nSummary:\n{resume.summary}")
        
        return '\n'.join(sections)
    
    def _call_llm(
        self,
        cv_text: str,
        job_title: str,
        job_description: str,
        required_skills: str,
        preferred_skills: str
    ) -> Dict[str, Any]:
        """
        Call OpenAI ChatGPT API
        """
        # Format prompt
        user_prompt = self.DEFAULT_USER_PROMPT.format(
            job_title=job_title,
            job_description=job_description,
            cv_text=cv_text,
            required_skills=required_skills or "Not specified",
            preferred_skills=preferred_skills or "Not specified"
        )
        
        # API call
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}  # Force JSON output
            )
            
            # Extract data
            message = response.choices[0].message.content
            usage = response.usage
            
            # Calculate cost (gpt-4o-mini pricing as of Dec 2024)
            # Input: $0.150 per 1M tokens, Output: $0.600 per 1M tokens
            input_cost = (usage.prompt_tokens / 1_000_000) * 0.150
            output_cost = (usage.completion_tokens / 1_000_000) * 0.600
            total_cost = Decimal(str(input_cost + output_cost))
            
            return {
                'response': message,
                'raw_response': message,
                'prompt_tokens': usage.prompt_tokens,
                'completion_tokens': usage.completion_tokens,
                'cost': total_cost,
            }
            
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            raise
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        Parse JSON response from LLM
        """
        try:
            data = json.loads(response)
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            # Return minimal structure
            return {
                'overall_score': None,
                'strengths': [],
                'weaknesses': [],
                'hiring_recommendation': response,  # Store raw text
            }
    
    def _get_content_hash(self, text: str) -> str:
        """Generate SHA256 hash of content"""
        return hashlib.sha256(text.encode('utf-8')).hexdigest()
    
    def _get_from_cache(
        self,
        resume: 'ParsedResume',
        job: Optional['Job']
    ) -> Optional['CVAnalysisCache']:
        """
        Check if analysis exists in cache
        """
        from apps.resume_parser.models_llm import CVAnalysisCache
        
        cv_hash = self._get_content_hash(self._prepare_cv_text(resume))
        jd_hash = self._get_content_hash(job.description) if job else None
        
        try:
            cache_entry = CVAnalysisCache.objects.get(
                cv_content_hash=cv_hash,
                jd_content_hash=jd_hash,
                expires_at__gt=timezone.now()
            )
            return cache_entry
        except CVAnalysisCache.DoesNotExist:
            return None
    
    def _save_to_cache(
        self,
        resume: 'ParsedResume',
        job: Optional['Job'],
        analysis: 'CVAnalysis'
    ):
        """
        Save analysis to cache
        """
        from apps.resume_parser.models_llm import CVAnalysisCache
        
        cv_hash = self._get_content_hash(self._prepare_cv_text(resume))
        jd_hash = self._get_content_hash(job.description) if job else None
        
        # Cache for 30 days
        expires_at = timezone.now() + timedelta(days=30)
        
        CVAnalysisCache.objects.create(
            resume=resume,
            job=job,
            cv_content_hash=cv_hash,
            jd_content_hash=jd_hash,
            analysis=analysis,
            expires_at=expires_at
        )


# Convenience function
def analyze_cv_for_job(resume_id: str, job_id: str, user=None) -> 'CVAnalysis':
    """
    Quick analysis of CV for a specific job
    
    Usage:
        from apps.resume_parser.services_llm import analyze_cv_for_job
        analysis = analyze_cv_for_job(resume_id='...', job_id='...')
        print(f"Score: {analysis.overall_score}/100")
        print(f"Recommendation: {analysis.hiring_recommendation}")
    """
    service = LLMAnalysisService(provider='OPENAI')
    return service.analyze_cv(resume_id=resume_id, job_id=job_id, user=user)
