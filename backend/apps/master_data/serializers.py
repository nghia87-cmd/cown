from rest_framework import serializers
from typing import Any
from .models import (
    Industry, JobCategory, Skill, Location,
    Language, Currency, Degree, Tag, Benefit
)


class IndustrySerializer(serializers.ModelSerializer):
    jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Industry
        fields = ['id', 'name', 'slug', 'description', 'icon', 'jobs_count', 'is_active']
    
    def get_jobs_count(self, obj) -> int:
        return obj.companies.count()


class JobCategorySerializer(serializers.ModelSerializer):
    jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = JobCategory
        fields = ['id', 'name', 'slug', 'description', 'icon', 'parent', 'jobs_count', 'is_active']
    
    def get_jobs_count(self, obj) -> int:
        return obj.jobs.count()


class SkillSerializer(serializers.ModelSerializer):
    jobs_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Skill
        fields = ['id', 'name', 'slug', 'category', 'description', 'jobs_count', 'is_active']
    
    def get_jobs_count(self, obj) -> int:
        return obj.jobs.count()


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'slug', 'location_type', 'parent', 'country_code', 'latitude', 'longitude', 'is_active']


class LanguageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Language
        fields = ['id', 'name', 'code', 'is_active']


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ['id', 'name', 'code', 'symbol', 'is_active']


class DegreeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Degree
        fields = ['id', 'name', 'short_name', 'level', 'is_active']


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ['id', 'name', 'slug', 'is_active']


class BenefitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Benefit
        fields = ['id', 'name', 'slug', 'icon', 'description', 'is_active']
