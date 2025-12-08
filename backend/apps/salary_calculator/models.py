"""
Salary Calculator - Gross to Net conversion for Vietnam
SEO traffic magnet tool
"""
import uuid
from decimal import Decimal
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class TaxBracket(models.Model):
    """
    Progressive tax brackets for Vietnam PIT (Personal Income Tax)
    Updated according to current tax law
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Tax Range
    min_amount = models.DecimalField(
        _('minimum amount'),
        max_digits=12,
        decimal_places=2,
        help_text='Monthly taxable income from (VND)'
    )
    max_amount = models.DecimalField(
        _('maximum amount'),
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text='Monthly taxable income to (VND). NULL = unlimited'
    )
    
    # Tax Rate
    tax_rate = models.DecimalField(
        _('tax rate (%)'),
        max_digits=5,
        decimal_places=2,
        help_text='Tax percentage for this bracket'
    )
    
    # Year Applicable
    year = models.PositiveIntegerField(
        _('applicable year'),
        default=2025,
        help_text='Tax year this bracket applies to'
    )
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tax_brackets'
        verbose_name = _('tax bracket')
        verbose_name_plural = _('tax brackets')
        ordering = ['year', 'min_amount']
        indexes = [
            models.Index(fields=['year', 'is_active']),
        ]
    
    def __str__(self):
        max_display = f"{self.max_amount:,.0f}" if self.max_amount else "∞"
        return f"{self.min_amount:,.0f} - {max_display} VND: {self.tax_rate}%"


class SocialInsuranceRate(models.Model):
    """
    Social insurance contribution rates (BHXH, BHYT, BHTN)
    Rates change periodically, keep historical data
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Rates (%)
    employee_si_rate = models.DecimalField(
        _('employee social insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('8.00'),
        help_text='BHXH - Employee contribution'
    )
    employee_hi_rate = models.DecimalField(
        _('employee health insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.5'),
        help_text='BHYT - Employee contribution'
    )
    employee_ui_rate = models.DecimalField(
        _('employee unemployment insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='BHTN - Employee contribution'
    )
    
    employer_si_rate = models.DecimalField(
        _('employer social insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('17.5'),
        help_text='BHXH - Employer contribution'
    )
    employer_hi_rate = models.DecimalField(
        _('employer health insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('3.0'),
        help_text='BHYT - Employer contribution'
    )
    employer_ui_rate = models.DecimalField(
        _('employer unemployment insurance (%)'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.00'),
        help_text='BHTN - Employer contribution'
    )
    
    # Caps & Limits
    si_max_salary = models.DecimalField(
        _('max salary for SI calculation'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('36000000'),
        help_text='Max monthly salary subject to SI (VND)'
    )
    regional_min_wage = models.DecimalField(
        _('regional minimum wage'),
        max_digits=12,
        decimal_places=2,
        default=Decimal('4960000'),
        help_text='Base wage for region 1 (VND)'
    )
    
    # Effective Period
    effective_from = models.DateField(_('effective from'))
    effective_to = models.DateField(_('effective to'), null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(_('active'), default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'social_insurance_rates'
        verbose_name = _('social insurance rate')
        verbose_name_plural = _('social insurance rates')
        ordering = ['-effective_from']
    
    def __str__(self):
        return f"SI Rates from {self.effective_from}"
    
    @property
    def total_employee_rate(self):
        """Total employee contribution rate"""
        return self.employee_si_rate + self.employee_hi_rate + self.employee_ui_rate
    
    @property
    def total_employer_rate(self):
        """Total employer contribution rate"""
        return self.employer_si_rate + self.employer_hi_rate + self.employer_ui_rate


class SalaryCalculation(models.Model):
    """
    Store salary calculations for analytics & user history
    Track popular salary ranges for market insights
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # User (optional - for logged-in users)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='salary_calculations'
    )
    
    # Input Parameters
    gross_salary = models.DecimalField(
        _('gross salary'),
        max_digits=12,
        decimal_places=2,
        help_text='Monthly gross salary (VND)'
    )
    region = models.PositiveSmallIntegerField(
        _('region'),
        default=1,
        choices=[
            (1, 'Region 1 (Hanoi, HCM)'),
            (2, 'Region 2 (Major cities)'),
            (3, 'Region 3 (Other cities)'),
            (4, 'Region 4 (Rural areas)'),
        ],
        help_text='For minimum wage calculation'
    )
    
    # Number of Dependents (for tax deduction)
    num_dependents = models.PositiveSmallIntegerField(
        _('number of dependents'),
        default=0,
        help_text='For family deduction (4.4M VND per person)'
    )
    
    # Calculated Results (cache for performance)
    si_employee = models.DecimalField(
        _('employee SI contribution'),
        max_digits=12,
        decimal_places=2
    )
    hi_employee = models.DecimalField(
        _('employee HI contribution'),
        max_digits=12,
        decimal_places=2
    )
    ui_employee = models.DecimalField(
        _('employee UI contribution'),
        max_digits=12,
        decimal_places=2
    )
    
    taxable_income = models.DecimalField(
        _('taxable income'),
        max_digits=12,
        decimal_places=2
    )
    personal_income_tax = models.DecimalField(
        _('personal income tax'),
        max_digits=12,
        decimal_places=2
    )
    
    net_salary = models.DecimalField(
        _('net salary (take-home)'),
        max_digits=12,
        decimal_places=2
    )
    
    # Employer Costs (total cost to company)
    employer_si = models.DecimalField(
        _('employer SI cost'),
        max_digits=12,
        decimal_places=2
    )
    employer_hi = models.DecimalField(
        _('employer HI cost'),
        max_digits=12,
        decimal_places=2
    )
    employer_ui = models.DecimalField(
        _('employer UI cost'),
        max_digits=12,
        decimal_places=2
    )
    total_cost_to_company = models.DecimalField(
        _('total cost to company'),
        max_digits=12,
        decimal_places=2
    )
    
    # Metadata
    calculation_date = models.DateField(_('calculation date'), auto_now_add=True)
    ip_address = models.GenericIPAddressField(
        _('IP address'),
        null=True,
        blank=True,
        help_text='For analytics'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'salary_calculations'
        verbose_name = _('salary calculation')
        verbose_name_plural = _('salary calculations')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['gross_salary']),
            models.Index(fields=['-calculation_date']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Anonymous'
        return f"{user_email} - {self.gross_salary:,.0f} VND"
    
    @property
    def tax_rate_percentage(self):
        """Effective tax rate"""
        if self.gross_salary == 0:
            return Decimal('0.00')
        return (self.personal_income_tax / self.gross_salary * 100).quantize(Decimal('0.01'))
    
    @property
    def net_percentage(self):
        """Net salary as percentage of gross"""
        if self.gross_salary == 0:
            return Decimal('0.00')
        return (self.net_salary / self.gross_salary * 100).quantize(Decimal('0.01'))


class SalaryBenchmark(models.Model):
    """
    Market salary data for different roles/industries
    Used for "Market Comparison" feature in calculator
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Job Info
    job_title = models.CharField(_('job title'), max_length=200, db_index=True)
    industry = models.CharField(
        _('industry'),
        max_length=100,
        choices=[
            ('IT', 'Information Technology'),
            ('FINANCE', 'Finance & Banking'),
            ('MARKETING', 'Marketing & Sales'),
            ('MANUFACTURING', 'Manufacturing'),
            ('HEALTHCARE', 'Healthcare'),
            ('EDUCATION', 'Education'),
            ('RETAIL', 'Retail & E-commerce'),
            ('OTHER', 'Other'),
        ]
    )
    
    # Experience Level
    experience_level = models.CharField(
        _('experience level'),
        max_length=20,
        choices=[
            ('INTERN', 'Intern'),
            ('JUNIOR', 'Junior (0-2 years)'),
            ('MID', 'Mid-level (2-5 years)'),
            ('SENIOR', 'Senior (5-10 years)'),
            ('LEAD', 'Lead/Manager (10+ years)'),
        ]
    )
    
    # Location
    city = models.CharField(_('city'), max_length=100, default='Hanoi')
    
    # Salary Range (Gross)
    min_salary = models.DecimalField(
        _('minimum salary'),
        max_digits=12,
        decimal_places=2
    )
    avg_salary = models.DecimalField(
        _('average salary'),
        max_digits=12,
        decimal_places=2
    )
    max_salary = models.DecimalField(
        _('maximum salary'),
        max_digits=12,
        decimal_places=2
    )
    
    # Data Source & Quality
    sample_size = models.PositiveIntegerField(
        _('sample size'),
        default=0,
        help_text='Number of data points'
    )
    data_source = models.CharField(
        _('data source'),
        max_length=100,
        default='Platform Data',
        help_text='e.g., "Platform Data", "Survey", "External API"'
    )
    
    # Validity
    last_updated = models.DateField(_('last updated'))
    is_verified = models.BooleanField(_('verified'), default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'salary_benchmarks'
        verbose_name = _('salary benchmark')
        verbose_name_plural = _('salary benchmarks')
        unique_together = [['job_title', 'industry', 'experience_level', 'city']]
        ordering = ['job_title', 'experience_level']
        indexes = [
            models.Index(fields=['job_title', 'city']),
            models.Index(fields=['industry', 'experience_level']),
        ]
    
    def __str__(self):
        return f"{self.job_title} - {self.experience_level} in {self.city}"
