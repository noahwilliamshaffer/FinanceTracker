"""
Data Quality and Validation Engine
Comprehensive data validation, quality scoring, and automated correction pipelines
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import logging
import re
import json
from abc import ABC, abstractmethod
import warnings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ValidationSeverity(Enum):
    """Validation issue severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class DataQualityDimension(Enum):
    """Data quality dimensions"""
    COMPLETENESS = "completeness"
    ACCURACY = "accuracy"
    CONSISTENCY = "consistency"
    TIMELINESS = "timeliness"
    VALIDITY = "validity"
    UNIQUENESS = "uniqueness"

@dataclass
class ValidationResult:
    """Result of a validation check"""
    check_name: str
    dimension: DataQualityDimension
    severity: ValidationSeverity
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    affected_rows: List[int] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class DataQualityScore:
    """Overall data quality assessment"""
    overall_score: float  # 0-100
    dimension_scores: Dict[str, float]
    total_checks: int
    passed_checks: int
    failed_checks: int
    critical_issues: int
    error_issues: int
    warning_issues: int
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

class ValidationRule(ABC):
    """Abstract base class for validation rules"""
    
    def __init__(self, name: str, dimension: DataQualityDimension, 
                 severity: ValidationSeverity, description: str = ""):
        self.name = name
        self.dimension = dimension
        self.severity = severity
        self.description = description
    
    @abstractmethod
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        """Execute the validation rule"""
        pass

class CompletenessRule(ValidationRule):
    """Check for missing/null values"""
    
    def __init__(self, column: str, max_null_pct: float = 0.0, 
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(
            name=f"Completeness_{column}",
            dimension=DataQualityDimension.COMPLETENESS,
            severity=severity,
            description=f"Check for missing values in {column}"
        )
        self.column = column
        self.max_null_pct = max_null_pct
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Column '{self.column}' not found in dataset",
                details={'missing_column': self.column}
            )
        
        null_count = data[self.column].isnull().sum()
        total_count = len(data)
        null_pct = (null_count / total_count * 100) if total_count > 0 else 0
        
        passed = null_pct <= self.max_null_pct
        
        return ValidationResult(
            check_name=self.name,
            dimension=self.dimension,
            severity=self.severity,
            passed=passed,
            message=f"Column '{self.column}' has {null_pct:.1f}% missing values (threshold: {self.max_null_pct}%)",
            details={
                'null_count': null_count,
                'total_count': total_count,
                'null_percentage': null_pct,
                'threshold': self.max_null_pct
            },
            affected_rows=data[data[self.column].isnull()].index.tolist()
        )

class AccuracyRule(ValidationRule):
    """Check for data accuracy within expected ranges"""
    
    def __init__(self, column: str, min_value: Optional[float] = None, 
                 max_value: Optional[float] = None,
                 severity: ValidationSeverity = ValidationSeverity.WARNING):
        super().__init__(
            name=f"Accuracy_{column}",
            dimension=DataQualityDimension.ACCURACY,
            severity=severity,
            description=f"Check value ranges for {column}"
        )
        self.column = column
        self.min_value = min_value
        self.max_value = max_value
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Column '{self.column}' not found in dataset"
            )
        
        # Filter numeric data only
        numeric_data = pd.to_numeric(data[self.column], errors='coerce')
        invalid_rows = []
        
        if self.min_value is not None:
            invalid_rows.extend(data[numeric_data < self.min_value].index.tolist())
        
        if self.max_value is not None:
            invalid_rows.extend(data[numeric_data > self.max_value].index.tolist())
        
        invalid_rows = list(set(invalid_rows))  # Remove duplicates
        passed = len(invalid_rows) == 0
        
        return ValidationResult(
            check_name=self.name,
            dimension=self.dimension,
            severity=self.severity,
            passed=passed,
            message=f"Column '{self.column}' has {len(invalid_rows)} values outside expected range [{self.min_value}, {self.max_value}]",
            details={
                'min_value': self.min_value,
                'max_value': self.max_value,
                'invalid_count': len(invalid_rows),
                'data_min': float(numeric_data.min()) if not numeric_data.empty else None,
                'data_max': float(numeric_data.max()) if not numeric_data.empty else None
            },
            affected_rows=invalid_rows
        )

class ConsistencyRule(ValidationRule):
    """Check for data consistency across related fields"""
    
    def __init__(self, primary_column: str, reference_column: str, 
                 consistency_check: Callable[[Any, Any], bool],
                 severity: ValidationSeverity = ValidationSeverity.WARNING):
        super().__init__(
            name=f"Consistency_{primary_column}_{reference_column}",
            dimension=DataQualityDimension.CONSISTENCY,
            severity=severity,
            description=f"Check consistency between {primary_column} and {reference_column}"
        )
        self.primary_column = primary_column
        self.reference_column = reference_column
        self.consistency_check = consistency_check
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        missing_cols = []
        if self.primary_column not in data.columns:
            missing_cols.append(self.primary_column)
        if self.reference_column not in data.columns:
            missing_cols.append(self.reference_column)
        
        if missing_cols:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Columns not found: {missing_cols}"
            )
        
        inconsistent_rows = []
        
        for idx, row in data.iterrows():
            primary_val = row[self.primary_column]
            reference_val = row[self.reference_column]
            
            try:
                if not pd.isna(primary_val) and not pd.isna(reference_val):
                    if not self.consistency_check(primary_val, reference_val):
                        inconsistent_rows.append(idx)
            except Exception as e:
                logger.warning(f"Consistency check failed for row {idx}: {e}")
                inconsistent_rows.append(idx)
        
        passed = len(inconsistent_rows) == 0
        
        return ValidationResult(
            check_name=self.name,
            dimension=self.dimension,
            severity=self.severity,
            passed=passed,
            message=f"Found {len(inconsistent_rows)} inconsistent records between {self.primary_column} and {self.reference_column}",
            details={
                'primary_column': self.primary_column,
                'reference_column': self.reference_column,
                'inconsistent_count': len(inconsistent_rows)
            },
            affected_rows=inconsistent_rows
        )

class TimelinessRule(ValidationRule):
    """Check data freshness and timeliness"""
    
    def __init__(self, timestamp_column: str, max_age_hours: float = 24,
                 severity: ValidationSeverity = ValidationSeverity.WARNING):
        super().__init__(
            name=f"Timeliness_{timestamp_column}",
            dimension=DataQualityDimension.TIMELINESS,
            severity=severity,
            description=f"Check data freshness for {timestamp_column}"
        )
        self.timestamp_column = timestamp_column
        self.max_age_hours = max_age_hours
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        if self.timestamp_column not in data.columns:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Timestamp column '{self.timestamp_column}' not found"
            )
        
        try:
            timestamps = pd.to_datetime(data[self.timestamp_column], errors='coerce')
            current_time = datetime.now()
            max_age = timedelta(hours=self.max_age_hours)
            
            stale_rows = data[timestamps < (current_time - max_age)].index.tolist()
            
            passed = len(stale_rows) == 0
            
            oldest_timestamp = timestamps.min()
            newest_timestamp = timestamps.max()
            
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=self.severity,
                passed=passed,
                message=f"Found {len(stale_rows)} records older than {self.max_age_hours} hours",
                details={
                    'max_age_hours': self.max_age_hours,
                    'stale_count': len(stale_rows),
                    'oldest_record': oldest_timestamp.isoformat() if pd.notna(oldest_timestamp) else None,
                    'newest_record': newest_timestamp.isoformat() if pd.notna(newest_timestamp) else None
                },
                affected_rows=stale_rows
            )
            
        except Exception as e:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Error processing timestamps: {e}"
            )

class ValidityRule(ValidationRule):
    """Check data format validity (e.g., CUSIP format, email format)"""
    
    def __init__(self, column: str, pattern: str, pattern_name: str = "format",
                 severity: ValidationSeverity = ValidationSeverity.ERROR):
        super().__init__(
            name=f"Validity_{column}_{pattern_name}",
            dimension=DataQualityDimension.VALIDITY,
            severity=severity,
            description=f"Check {pattern_name} validity for {column}"
        )
        self.column = column
        self.pattern = pattern
        self.pattern_name = pattern_name
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        if self.column not in data.columns:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Column '{self.column}' not found"
            )
        
        try:
            # Filter out null values for validation
            non_null_data = data[data[self.column].notna()]
            
            if len(non_null_data) == 0:
                return ValidationResult(
                    check_name=self.name,
                    dimension=self.dimension,
                    severity=self.severity,
                    passed=True,
                    message=f"No non-null values to validate in {self.column}"
                )
            
            pattern_matches = non_null_data[self.column].astype(str).str.match(self.pattern, na=False)
            invalid_rows = non_null_data[~pattern_matches].index.tolist()
            
            passed = len(invalid_rows) == 0
            
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=self.severity,
                passed=passed,
                message=f"Found {len(invalid_rows)} invalid {self.pattern_name} formats in {self.column}",
                details={
                    'pattern': self.pattern,
                    'pattern_name': self.pattern_name,
                    'invalid_count': len(invalid_rows),
                    'total_checked': len(non_null_data)
                },
                affected_rows=invalid_rows
            )
            
        except Exception as e:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.ERROR,
                passed=False,
                message=f"Error validating pattern: {e}"
            )

class UniquenessRule(ValidationRule):
    """Check for duplicate values"""
    
    def __init__(self, columns: List[str], severity: ValidationSeverity = ValidationSeverity.WARNING):
        column_str = "_".join(columns)
        super().__init__(
            name=f"Uniqueness_{column_str}",
            dimension=DataQualityDimension.UNIQUENESS,
            severity=severity,
            description=f"Check for duplicates in {columns}"
        )
        self.columns = columns if isinstance(columns, list) else [columns]
    
    def validate(self, data: pd.DataFrame) -> ValidationResult:
        missing_cols = [col for col in self.columns if col not in data.columns]
        
        if missing_cols:
            return ValidationResult(
                check_name=self.name,
                dimension=self.dimension,
                severity=ValidationSeverity.CRITICAL,
                passed=False,
                message=f"Columns not found: {missing_cols}"
            )
        
        # Find duplicates
        duplicates = data.duplicated(subset=self.columns, keep=False)
        duplicate_rows = data[duplicates].index.tolist()
        
        passed = len(duplicate_rows) == 0
        
        # Get duplicate groups
        duplicate_groups = []
        if len(duplicate_rows) > 0:
            duplicate_data = data[duplicates]
            for group_values, group_df in duplicate_data.groupby(self.columns):
                duplicate_groups.append({
                    'values': dict(zip(self.columns, group_values)) if len(self.columns) > 1 else {self.columns[0]: group_values},
                    'count': len(group_df),
                    'rows': group_df.index.tolist()
                })
        
        return ValidationResult(
            check_name=self.name,
            dimension=self.dimension,
            severity=self.severity,
            passed=passed,
            message=f"Found {len(duplicate_rows)} duplicate records across columns {self.columns}",
            details={
                'columns': self.columns,
                'duplicate_count': len(duplicate_rows),
                'duplicate_groups': duplicate_groups[:10]  # Limit to first 10 groups
            },
            affected_rows=duplicate_rows
        )

class FinancialDataValidator:
    """Specialized validator for financial market data"""
    
    @staticmethod
    def create_treasury_validation_rules() -> List[ValidationRule]:
        """Create validation rules specific to Treasury data"""
        rules = []
        
        # Completeness checks
        rules.append(CompletenessRule('cusip', max_null_pct=0))
        rules.append(CompletenessRule('price', max_null_pct=5))
        rules.append(CompletenessRule('yield', max_null_pct=5))
        
        # Accuracy checks  
        rules.append(AccuracyRule('price', min_value=50.0, max_value=150.0))  # Bond prices
        rules.append(AccuracyRule('yield', min_value=-0.01, max_value=0.20))  # Yield rates
        rules.append(AccuracyRule('spread_bps', min_value=-500, max_value=2000))  # Spreads in bps
        
        # Validity checks
        rules.append(ValidityRule('cusip', r'^[0-9]{8}[A-Z0-9]{1}[0-9]{1}$', 'CUSIP'))
        
        # Consistency checks
        def price_yield_consistency(price: float, yield_rate: float) -> bool:
            """Check if price and yield are roughly consistent (inverse relationship)"""
            try:
                # Very simplified check - in practice would use proper bond math
                return (price < 100 and yield_rate > 0.03) or (price > 100 and yield_rate < 0.06)
            except:
                return True  # Skip check if values can't be compared
        
        rules.append(ConsistencyRule('price', 'yield', price_yield_consistency))
        
        # Uniqueness check
        rules.append(UniquenessRule(['cusip', 'timestamp']))
        
        return rules
    
    @staticmethod
    def create_repo_validation_rules() -> List[ValidationRule]:
        """Create validation rules specific to repo data"""
        rules = []
        
        # Completeness
        rules.append(CompletenessRule('spread_bps', max_null_pct=0))
        rules.append(CompletenessRule('volume_mm', max_null_pct=10))
        rules.append(CompletenessRule('term', max_null_pct=0))
        
        # Accuracy
        rules.append(AccuracyRule('spread_bps', min_value=-50, max_value=500))
        rules.append(AccuracyRule('volume_mm', min_value=0.1, max_value=10000))
        
        # Timeliness
        rules.append(TimelinessRule('timestamp', max_age_hours=6))
        
        return rules

class DataQualityEngine:
    """Main data quality assessment engine"""
    
    def __init__(self):
        self.validation_rules: List[ValidationRule] = []
        self.validation_history: List[Dict[str, Any]] = []
        
    def add_rule(self, rule: ValidationRule):
        """Add a validation rule"""
        self.validation_rules.append(rule)
        logger.info(f"Added validation rule: {rule.name}")
    
    def add_rules(self, rules: List[ValidationRule]):
        """Add multiple validation rules"""
        for rule in rules:
            self.add_rule(rule)
    
    def validate_dataset(self, data: pd.DataFrame, dataset_name: str = "dataset") -> Tuple[DataQualityScore, List[ValidationResult]]:
        """Validate a dataset against all rules"""
        logger.info(f"Starting validation of {dataset_name} with {len(self.validation_rules)} rules")
        
        results = []
        
        # Run all validation rules
        for rule in self.validation_rules:
            try:
                result = rule.validate(data)
                results.append(result)
                
                if not result.passed:
                    logger.warning(f"Validation failed: {result.check_name} - {result.message}")
                    
            except Exception as e:
                logger.error(f"Error running validation rule {rule.name}: {e}")
                results.append(ValidationResult(
                    check_name=rule.name,
                    dimension=rule.dimension,
                    severity=ValidationSeverity.ERROR,
                    passed=False,
                    message=f"Validation rule execution failed: {e}"
                ))
        
        # Calculate quality score
        quality_score = self._calculate_quality_score(results)
        
        # Store validation history
        validation_record = {
            'timestamp': datetime.now().isoformat(),
            'dataset_name': dataset_name,
            'quality_score': quality_score.overall_score,
            'total_checks': quality_score.total_checks,
            'failed_checks': quality_score.failed_checks,
            'critical_issues': quality_score.critical_issues
        }
        self.validation_history.append(validation_record)
        
        logger.info(f"Validation complete. Overall quality score: {quality_score.overall_score:.1f}/100")
        
        return quality_score, results
    
    def _calculate_quality_score(self, results: List[ValidationResult]) -> DataQualityScore:
        """Calculate overall data quality score"""
        if not results:
            return DataQualityScore(
                overall_score=0.0,
                dimension_scores={},
                total_checks=0,
                passed_checks=0,
                failed_checks=0,
                critical_issues=0,
                error_issues=0,
                warning_issues=0
            )
        
        total_checks = len(results)
        passed_checks = sum(1 for r in results if r.passed)
        failed_checks = total_checks - passed_checks
        
        # Count by severity
        critical_issues = sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.CRITICAL)
        error_issues = sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.ERROR)
        warning_issues = sum(1 for r in results if not r.passed and r.severity == ValidationSeverity.WARNING)
        
        # Calculate dimension scores
        dimension_scores = {}
        for dimension in DataQualityDimension:
            dimension_results = [r for r in results if r.dimension == dimension]
            if dimension_results:
                dimension_passed = sum(1 for r in dimension_results if r.passed)
                dimension_score = (dimension_passed / len(dimension_results)) * 100
                dimension_scores[dimension.value] = dimension_score
        
        # Calculate overall score with severity weighting
        severity_weights = {
            ValidationSeverity.CRITICAL: -50,
            ValidationSeverity.ERROR: -20,
            ValidationSeverity.WARNING: -5,
            ValidationSeverity.INFO: -1
        }
        
        score_deductions = 0
        for result in results:
            if not result.passed:
                score_deductions += severity_weights.get(result.severity, -10)
        
        # Start with 100 and deduct based on failures
        overall_score = max(0, 100 + score_deductions)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(results)
        
        return DataQualityScore(
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            total_checks=total_checks,
            passed_checks=passed_checks,
            failed_checks=failed_checks,
            critical_issues=critical_issues,
            error_issues=error_issues,
            warning_issues=warning_issues,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, results: List[ValidationResult]) -> List[str]:
        """Generate recommendations based on validation results"""
        recommendations = []
        
        # Critical issues
        critical_results = [r for r in results if not r.passed and r.severity == ValidationSeverity.CRITICAL]
        if critical_results:
            recommendations.append(f"🚨 Address {len(critical_results)} critical data issues immediately")
        
        # Completeness issues
        completeness_failures = [r for r in results if not r.passed and r.dimension == DataQualityDimension.COMPLETENESS]
        if completeness_failures:
            recommendations.append(f"📊 Improve data completeness - {len(completeness_failures)} fields have missing values")
        
        # Accuracy issues
        accuracy_failures = [r for r in results if not r.passed and r.dimension == DataQualityDimension.ACCURACY]
        if accuracy_failures:
            recommendations.append(f"🎯 Review data accuracy - {len(accuracy_failures)} fields have values outside expected ranges")
        
        # Timeliness issues
        timeliness_failures = [r for r in results if not r.passed and r.dimension == DataQualityDimension.TIMELINESS]
        if timeliness_failures:
            recommendations.append("⏰ Improve data freshness - some records are stale")
        
        # Format issues
        validity_failures = [r for r in results if not r.passed and r.dimension == DataQualityDimension.VALIDITY]
        if validity_failures:
            recommendations.append("📝 Fix data format issues - some values don't match expected patterns")
        
        return recommendations
    
    def get_quality_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get data quality trend over time"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        recent_validations = [
            v for v in self.validation_history 
            if datetime.fromisoformat(v['timestamp']) > cutoff_date
        ]
        
        return sorted(recent_validations, key=lambda x: x['timestamp'])
    
    def export_validation_report(self, results: List[ValidationResult], 
                               quality_score: DataQualityScore) -> Dict[str, Any]:
        """Export comprehensive validation report"""
        return {
            'summary': {
                'overall_score': quality_score.overall_score,
                'total_checks': quality_score.total_checks,
                'passed_checks': quality_score.passed_checks,
                'failed_checks': quality_score.failed_checks,
                'critical_issues': quality_score.critical_issues,
                'error_issues': quality_score.error_issues,
                'warning_issues': quality_score.warning_issues
            },
            'dimension_scores': quality_score.dimension_scores,
            'recommendations': quality_score.recommendations,
            'detailed_results': [
                {
                    'check_name': r.check_name,
                    'dimension': r.dimension.value,
                    'severity': r.severity.value,
                    'passed': r.passed,
                    'message': r.message,
                    'details': r.details,
                    'affected_rows_count': len(r.affected_rows)
                }
                for r in results
            ],
            'timestamp': datetime.now().isoformat()
        }

# Example usage and testing
if __name__ == "__main__":
    # Create sample financial data
    sample_data = pd.DataFrame({
        'cusip': ['912828XG8', '912828YK0', '912810RZ3', 'INVALID01', '912828XG8'],  # Duplicate and invalid
        'price': [99.5, 101.2, 98.8, 150.5, 99.6],  # One out of range
        'yield': [0.045, 0.048, 0.042, 0.035, None],  # One missing
        'spread_bps': [25.5, 18.2, 32.1, 15.8, 28.3],
        'volume_mm': [10.5, 5.2, 8.7, 12.1, 6.8],
        'term': ['10Y', '2Y', '30Y', '5Y', '10Y'],
        'timestamp': [
            datetime.now() - timedelta(hours=1),
            datetime.now() - timedelta(hours=2),
            datetime.now() - timedelta(hours=25),  # Stale
            datetime.now() - timedelta(minutes=30),
            datetime.now() - timedelta(hours=1)
        ]
    })
    
    # Create data quality engine
    engine = DataQualityEngine()
    
    # Add Treasury validation rules
    treasury_rules = FinancialDataValidator.create_treasury_validation_rules()
    engine.add_rules(treasury_rules)
    
    # Add repo validation rules
    repo_rules = FinancialDataValidator.create_repo_validation_rules()
    engine.add_rules(repo_rules)
    
    # Validate the dataset
    quality_score, validation_results = engine.validate_dataset(sample_data, "Treasury Sample Data")
    
    # Print results
    print(f"Data Quality Score: {quality_score.overall_score:.1f}/100")
    print(f"Checks: {quality_score.passed_checks}/{quality_score.total_checks} passed")
    print(f"Issues: {quality_score.critical_issues} critical, {quality_score.error_issues} errors, {quality_score.warning_issues} warnings")
    
    print("\nDimension Scores:")
    for dimension, score in quality_score.dimension_scores.items():
        print(f"  {dimension}: {score:.1f}/100")
    
    print("\nRecommendations:")
    for rec in quality_score.recommendations:
        print(f"  • {rec}")
    
    print("\nFailed Validations:")
    for result in validation_results:
        if not result.passed:
            print(f"  ❌ {result.check_name}: {result.message}")
    
    # Export report
    report = engine.export_validation_report(validation_results, quality_score)
    print(f"\nGenerated validation report with {len(report['detailed_results'])} checks")
