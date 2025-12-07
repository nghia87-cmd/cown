from rest_framework import serializers
from django.db import transaction
from django.contrib.auth import get_user_model
from typing import List
from .models import Company, CompanyMember, CompanyReview, CompanyFollower

User = get_user_model()


class CompanyMemberSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CompanyMember
        fields = [
            'id', 'user', 'user_email', 'user_name', 'role',
            'can_post_jobs', 'can_manage_jobs', 'can_view_applications',
            'can_manage_members', 'is_active', 'joined_at'
        ]
        read_only_fields = ['id', 'joined_at']


class CompanyReviewSerializer(serializers.ModelSerializer):
    reviewer_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CompanyReview
        fields = [
            'id', 'company', 'user', 'reviewer_name', 'title', 'review_text',
            'overall_rating', 'work_life_balance', 'salary_benefits', 'culture',
            'career_opportunities', 'management', 'position', 'employment_status',
            'pros', 'cons', 'is_verified', 'is_approved', 'is_featured',
            'helpful_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'is_verified', 'is_approved', 'is_featured', 'helpful_count', 'created_at', 'updated_at']
    
    def validate_overall_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5")
        return value


class CompanyFollowerSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CompanyFollower
        fields = ['id', 'user', 'user_name', 'company', 'followed_at']
        read_only_fields = ['id', 'followed_at']


class CompanyListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for company listings"""
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    is_following = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'slug', 'logo', 'industry', 'industry_name',
            'city', 'province', 'country', 'size', 'website',
            'total_jobs', 'active_jobs', 'is_verified',
            'is_following', 'created_at'
        ]
    
    def get_is_following(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CompanyFollower.objects.filter(
                company=obj, 
                user=request.user
            ).exists()
        return False


class CompanyDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer for company profile"""
    industry_name = serializers.CharField(source='industry.name', read_only=True)
    members_count = serializers.SerializerMethodField()
    followers_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()
    recent_reviews = serializers.SerializerMethodField()
    
    class Meta:
        model = Company
        fields = [
            'id', 'name', 'slug', 'tagline', 'description', 'logo', 'cover_image',
            'industry', 'industry_name', 'size', 'founded_year', 'website',
            'email', 'phone', 'address', 'city', 'province', 'country',
            'linkedin_url', 'facebook_url', 'twitter_url',
            'total_jobs', 'active_jobs', 'total_employees',
            'is_verified', 'verified_at', 'is_active', 'is_featured',
            'members_count', 'followers_count', 'is_following', 'recent_reviews',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'slug', 'total_jobs', 'active_jobs',
            'is_verified', 'verified_at', 'created_at', 'updated_at'
        ]
    
    def get_members_count(self, obj) -> int:
        return obj.members.filter(is_active=True).count()
    
    def get_followers_count(self, obj) -> int:
        return obj.followers.count()
    
    def get_is_following(self, obj) -> bool:
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return CompanyFollower.objects.filter(
                company=obj,
                user=request.user
            ).exists()
        return False
    
    def get_recent_reviews(self, obj) -> List[dict]:
        reviews = obj.reviews.filter(is_approved=True).order_by('-created_at')[:5]
        return CompanyReviewSerializer(reviews, many=True).data


class CompanyCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating company"""
    
    class Meta:
        model = Company
        fields = [
            'name', 'tagline', 'description', 'logo', 'cover_image',
            'industry', 'size', 'founded_year', 'website',
            'email', 'phone', 'address', 'city', 'province', 'country',
            'linkedin_url', 'facebook_url', 'twitter_url'
        ]
    
    def validate_website(self, value):
        if value and not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("Website must start with http:// or https://")
        return value
    
    def validate_founded_year(self, value):
        from datetime import datetime
        current_year = datetime.now().year
        if value and (value < 1800 or value > current_year):
            raise serializers.ValidationError(f"Founded year must be between 1800 and {current_year}")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        company = Company.objects.create(**validated_data)
        
        # Add creator as owner
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            company.owner = request.user
            company.save(update_fields=['owner'])
            
            CompanyMember.objects.create(
                company=company,
                user=request.user,
                role='OWNER',
                is_active=True,
                can_manage_members=True
            )
        
        return company
    
    @transaction.atomic
    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        return instance


class CompanyStatsSerializer(serializers.Serializer):
    """Statistics for company dashboard"""
    total_jobs = serializers.IntegerField()
    active_jobs = serializers.IntegerField()
    total_applications = serializers.IntegerField()
    pending_applications = serializers.IntegerField()
    total_views = serializers.IntegerField()
    total_followers = serializers.IntegerField()
    avg_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
