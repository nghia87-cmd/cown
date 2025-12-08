"""
Salary Calculator Service
Business logic for Gross-Net conversion
"""
from decimal import Decimal
from typing import Dict, Optional
from datetime import date
from django.db import models
from .models import TaxBracket, SocialInsuranceRate, SalaryCalculation


class SalaryCalculatorService:
    """
    Calculate Net salary from Gross and vice versa
    Follows Vietnam tax & social insurance regulations
    """
    
    # Standard deductions (2025)
    PERSONAL_DEDUCTION = Decimal('11000000')  # 11M VND per month
    DEPENDENT_DEDUCTION = Decimal('4400000')  # 4.4M VND per dependent
    
    def __init__(self, calculation_date: Optional[date] = None):
        """
        Initialize calculator with rates for specific date
        
        Args:
            calculation_date: Date to calculate for (defaults to today)
        """
        self.calculation_date = calculation_date or date.today()
        self.si_rates = self._get_si_rates()
        self.tax_brackets = self._get_tax_brackets()
    
    def _get_si_rates(self) -> SocialInsuranceRate:
        """Get active social insurance rates"""
        rates = SocialInsuranceRate.objects.filter(
            is_active=True,
            effective_from__lte=self.calculation_date
        ).filter(
            models.Q(effective_to__isnull=True) | models.Q(effective_to__gte=self.calculation_date)
        ).first()
        
        if not rates:
            raise ValueError("No active social insurance rates found")
        
        return rates
    
    def _get_tax_brackets(self) -> list:
        """Get active tax brackets for the year"""
        year = self.calculation_date.year
        brackets = TaxBracket.objects.filter(
            year=year,
            is_active=True
        ).order_by('min_amount')
        
        if not brackets.exists():
            raise ValueError(f"No tax brackets found for year {year}")
        
        return list(brackets)
    
    def calculate_net_from_gross(
        self,
        gross_salary: Decimal,
        num_dependents: int = 0,
        region: int = 1,
        user=None,
        ip_address: str = None
    ) -> Dict[str, Decimal]:
        """
        Calculate net salary from gross
        
        Args:
            gross_salary: Monthly gross salary (VND)
            num_dependents: Number of dependents for tax deduction
            region: Region for minimum wage (1-4)
            user: User object (optional)
            ip_address: Client IP for analytics (optional)
        
        Returns:
            Dict with detailed breakdown:
            {
                'gross_salary': Decimal,
                'si_employee': Decimal,
                'hi_employee': Decimal,
                'ui_employee': Decimal,
                'total_insurance': Decimal,
                'income_before_tax': Decimal,
                'personal_deduction': Decimal,
                'dependent_deduction': Decimal,
                'total_deduction': Decimal,
                'taxable_income': Decimal,
                'personal_income_tax': Decimal,
                'net_salary': Decimal,
                'employer_si': Decimal,
                'employer_hi': Decimal,
                'employer_ui': Decimal,
                'total_employer_cost': Decimal,
                'total_cost_to_company': Decimal,
                'tax_rate_percentage': Decimal,
                'net_percentage': Decimal,
            }
        """
        # Step 1: Calculate social insurance base
        si_base = min(gross_salary, self.si_rates.si_max_salary)
        
        # Step 2: Employee insurance contributions
        si_employee = si_base * (self.si_rates.employee_si_rate / 100)
        hi_employee = si_base * (self.si_rates.employee_hi_rate / 100)
        ui_employee = si_base * (self.si_rates.employee_ui_rate / 100)
        total_insurance = si_employee + hi_employee + ui_employee
        
        # Step 3: Income before tax
        income_before_tax = gross_salary - total_insurance
        
        # Step 4: Tax deductions
        personal_deduction = self.PERSONAL_DEDUCTION
        dependent_deduction = self.DEPENDENT_DEDUCTION * num_dependents
        total_deduction = personal_deduction + dependent_deduction
        
        # Step 5: Taxable income
        taxable_income = max(Decimal('0'), income_before_tax - total_deduction)
        
        # Step 6: Calculate PIT (Progressive tax)
        pit = self._calculate_progressive_tax(taxable_income)
        
        # Step 7: Net salary
        net_salary = income_before_tax - pit
        
        # Step 8: Employer costs
        employer_si = si_base * (self.si_rates.employer_si_rate / 100)
        employer_hi = si_base * (self.si_rates.employer_hi_rate / 100)
        employer_ui = si_base * (self.si_rates.employer_ui_rate / 100)
        total_employer_cost = employer_si + employer_hi + employer_ui
        total_cost_to_company = gross_salary + total_employer_cost
        
        # Prepare result
        result = {
            'gross_salary': gross_salary.quantize(Decimal('0.01')),
            'si_employee': si_employee.quantize(Decimal('0.01')),
            'hi_employee': hi_employee.quantize(Decimal('0.01')),
            'ui_employee': ui_employee.quantize(Decimal('0.01')),
            'total_insurance': total_insurance.quantize(Decimal('0.01')),
            'income_before_tax': income_before_tax.quantize(Decimal('0.01')),
            'personal_deduction': personal_deduction,
            'dependent_deduction': dependent_deduction,
            'total_deduction': total_deduction,
            'taxable_income': taxable_income.quantize(Decimal('0.01')),
            'personal_income_tax': pit.quantize(Decimal('0.01')),
            'net_salary': net_salary.quantize(Decimal('0.01')),
            'employer_si': employer_si.quantize(Decimal('0.01')),
            'employer_hi': employer_hi.quantize(Decimal('0.01')),
            'employer_ui': employer_ui.quantize(Decimal('0.01')),
            'total_employer_cost': total_employer_cost.quantize(Decimal('0.01')),
            'total_cost_to_company': total_cost_to_company.quantize(Decimal('0.01')),
            'tax_rate_percentage': (pit / gross_salary * 100).quantize(Decimal('0.01')) if gross_salary > 0 else Decimal('0.00'),
            'net_percentage': (net_salary / gross_salary * 100).quantize(Decimal('0.01')) if gross_salary > 0 else Decimal('0.00'),
        }
        
        # Save calculation for analytics
        self._save_calculation(
            result=result,
            num_dependents=num_dependents,
            region=region,
            user=user,
            ip_address=ip_address
        )
        
        return result
    
    def calculate_gross_from_net(
        self,
        target_net: Decimal,
        num_dependents: int = 0,
        region: int = 1,
        max_iterations: int = 50
    ) -> Dict[str, Decimal]:
        """
        Calculate gross salary needed to achieve target net (reverse calculation)
        Uses iterative approximation method
        
        Args:
            target_net: Desired net salary (VND)
            num_dependents: Number of dependents
            region: Region for minimum wage
            max_iterations: Maximum iterations for convergence
        
        Returns:
            Same structure as calculate_net_from_gross
        """
        # Initial guess: net * 1.3 (rough estimate)
        gross_estimate = target_net * Decimal('1.3')
        
        # Iterative refinement
        for i in range(max_iterations):
            result = self.calculate_net_from_gross(
                gross_salary=gross_estimate,
                num_dependents=num_dependents,
                region=region
            )
            
            diff = result['net_salary'] - target_net
            
            # Converged within 1000 VND
            if abs(diff) < 1000:
                return result
            
            # Adjust estimate
            # If net is too high, reduce gross; if too low, increase
            adjustment_rate = Decimal('0.5')  # Damping factor
            gross_estimate -= diff * adjustment_rate
        
        # Return best approximation after max iterations
        return result
    
    def _calculate_progressive_tax(self, taxable_income: Decimal) -> Decimal:
        """
        Calculate PIT using progressive tax brackets
        
        Vietnam PIT (2025):
        - 0 to 5M: 5%
        - 5M to 10M: 10%
        - 10M to 18M: 15%
        - 18M to 32M: 20%
        - 32M to 52M: 25%
        - 52M to 80M: 30%
        - Above 80M: 35%
        """
        if taxable_income <= 0:
            return Decimal('0')
        
        total_tax = Decimal('0')
        remaining_income = taxable_income
        
        for i, bracket in enumerate(self.tax_brackets):
            # Determine bracket range
            bracket_min = bracket.min_amount
            bracket_max = bracket.max_amount if bracket.max_amount else Decimal('999999999999')
            
            # Calculate taxable amount in this bracket
            if remaining_income <= 0:
                break
            
            if i == 0:
                # First bracket: tax from 0
                taxable_in_bracket = min(remaining_income, bracket_max)
            else:
                # Subsequent brackets: tax the portion in this range
                if remaining_income + (taxable_income - remaining_income) <= bracket_min:
                    continue
                
                amount_in_bracket = min(
                    remaining_income,
                    bracket_max - bracket_min
                )
                taxable_in_bracket = max(Decimal('0'), amount_in_bracket)
            
            # Apply tax rate
            tax_in_bracket = taxable_in_bracket * (bracket.tax_rate / 100)
            total_tax += tax_in_bracket
            remaining_income -= taxable_in_bracket
        
        return total_tax
    
    def _save_calculation(
        self,
        result: Dict,
        num_dependents: int,
        region: int,
        user,
        ip_address: str
    ):
        """Save calculation to database for analytics"""
        try:
            SalaryCalculation.objects.create(
                user=user,
                gross_salary=result['gross_salary'],
                region=region,
                num_dependents=num_dependents,
                si_employee=result['si_employee'],
                hi_employee=result['hi_employee'],
                ui_employee=result['ui_employee'],
                taxable_income=result['taxable_income'],
                personal_income_tax=result['personal_income_tax'],
                net_salary=result['net_salary'],
                employer_si=result['employer_si'],
                employer_hi=result['employer_hi'],
                employer_ui=result['employer_ui'],
                total_cost_to_company=result['total_cost_to_company'],
                ip_address=ip_address,
            )
        except Exception as e:
            # Don't fail calculation if save fails
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to save salary calculation: {e}")
    
    def get_salary_comparison(
        self,
        gross_salary: Decimal,
        job_title: str = None,
        industry: str = None,
        experience_level: str = None,
        city: str = 'Hanoi'
    ) -> Dict:
        """
        Compare salary with market benchmarks
        
        Returns:
            {
                'your_salary': Decimal,
                'market_min': Decimal,
                'market_avg': Decimal,
                'market_max': Decimal,
                'percentile': Decimal,  # Where you rank (0-100)
                'comparison': str,  # 'below', 'average', 'above'
            }
        """
        from .models import SalaryBenchmark
        
        filters = {'city': city}
        if job_title:
            filters['job_title__icontains'] = job_title
        if industry:
            filters['industry'] = industry
        if experience_level:
            filters['experience_level'] = experience_level
        
        benchmark = SalaryBenchmark.objects.filter(**filters).first()
        
        if not benchmark:
            return {
                'your_salary': gross_salary,
                'market_data_available': False,
            }
        
        # Calculate percentile
        salary_range = benchmark.max_salary - benchmark.min_salary
        if salary_range > 0:
            position = gross_salary - benchmark.min_salary
            percentile = min(Decimal('100'), max(Decimal('0'), (position / salary_range * 100)))
        else:
            percentile = Decimal('50')
        
        # Determine comparison
        if gross_salary < benchmark.avg_salary * Decimal('0.9'):
            comparison = 'below'
        elif gross_salary > benchmark.avg_salary * Decimal('1.1'):
            comparison = 'above'
        else:
            comparison = 'average'
        
        return {
            'your_salary': gross_salary,
            'market_min': benchmark.min_salary,
            'market_avg': benchmark.avg_salary,
            'market_max': benchmark.max_salary,
            'percentile': percentile.quantize(Decimal('0.01')),
            'comparison': comparison,
            'market_data_available': True,
            'sample_size': benchmark.sample_size,
        }


# Convenience function
def calculate_salary(gross: float, dependents: int = 0, user=None) -> dict:
    """
    Quick salary calculation function
    
    Usage:
        result = calculate_salary(gross=20000000, dependents=2)
        print(f"Net: {result['net_salary']:,.0f} VND")
    """
    calculator = SalaryCalculatorService()
    return calculator.calculate_net_from_gross(
        gross_salary=Decimal(str(gross)),
        num_dependents=dependents,
        user=user
    )
