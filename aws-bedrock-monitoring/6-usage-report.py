#!/usr/bin/env python3
"""
AWS Bedrock Usage Report Generator

This script generates comprehensive usage reports for AWS Bedrock API calls,
including cost analysis, performance metrics, and monthly projections.

Usage:
    python3 6-usage-report.py [--hours HOURS] [--region REGION] [--output FORMAT]

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 7.3
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict
import boto3
from botocore.exceptions import ClientError, NoCredentialsError

# Import shared modules
sys.path.append('src')
from config import MonitoringConfiguration, load_config_from_env
from utils import log_operation, validate_aws_region, get_aws_account_id, get_aws_region


@dataclass
class ModelUsage:
    """Usage statistics for a specific model."""
    invocations: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_latency: float = 0.0
    error_count: int = 0
    
    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        return self.total_latency / self.invocations if self.invocations > 0 else 0.0


@dataclass
class UsageReport:
    """Complete usage report structure."""
    period: Dict[str, Any]
    summary: Dict[str, Any]
    by_model: Dict[str, Dict[str, Any]]
    projections: Dict[str, Any]
    performance: Dict[str, Any]


class BedrockPricing:
    """AWS Bedrock pricing information (as of 2024)."""
    
    # Pricing per 1000 tokens (input/output) in USD
    PRICING = {
        'anthropic.claude-3-sonnet-20240229-v1:0': {
            'input': 0.003,   # $3 per 1M input tokens
            'output': 0.015   # $15 per 1M output tokens
        },
        'anthropic.claude-3-opus-20240229-v1:0': {
            'input': 0.015,   # $15 per 1M input tokens
            'output': 0.075   # $75 per 1M output tokens
        },
        'anthropic.claude-3-haiku-20240307-v1:0': {
            'input': 0.00025, # $0.25 per 1M input tokens
            'output': 0.00125 # $1.25 per 1M output tokens
        },
        'anthropic.claude-instant-v1': {
            'input': 0.0008,  # $0.80 per 1M input tokens
            'output': 0.0024  # $2.40 per 1M output tokens
        }
    }
    
    @classmethod
    def calculate_cost(cls, model_id: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for given token usage."""
        if model_id not in cls.PRICING:
            # Default pricing for unknown models (use Sonnet rates)
            pricing = cls.PRICING['anthropic.claude-3-sonnet-20240229-v1:0']
        else:
            pricing = cls.PRICING[model_id]
        
        input_cost = (input_tokens / 1000) * pricing['input']
        output_cost = (output_tokens / 1000) * pricing['output']
        
        return input_cost + output_cost


class UsageReportGenerator:
    """Generates comprehensive Bedrock usage reports."""
    
    def __init__(self, region: str = None):
        """Initialize the report generator."""
        try:
            self.config = load_config_from_env()
        except Exception as e:
            # If config loading fails, use defaults
            self.config = MonitoringConfiguration()
            log_operation("CONFIG_LOAD", "Environment", False, f"Using defaults: {str(e)}")
        
        self.region = region or self.config.dashboard.region
        
        try:
            self.cloudwatch = boto3.client('cloudwatch', region_name=self.region)
            self.logs = boto3.client('logs', region_name=self.region)
            
            # Test connectivity
            self.cloudwatch.list_metrics(Namespace='AWS/Bedrock', MaxRecords=1)
        except NoCredentialsError:
            raise RuntimeError("AWS credentials not configured. Please run 'aws configure'.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'UnauthorizedOperation':
                raise RuntimeError("Insufficient AWS permissions for CloudWatch access.")
            else:
                raise RuntimeError(f"AWS service error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize AWS clients: {str(e)}")
    
    def get_metrics_data(self, start_time: datetime, end_time: datetime) -> Dict[str, ModelUsage]:
        """Retrieve CloudWatch metrics data for the specified time period."""
        model_usage = {}
        
        try:
            # Get list of available models from metrics
            models = self._get_available_models(start_time, end_time)
            
            if not models:
                log_operation("GET_MODELS", "CloudWatch", False, "No models found with metrics in time period")
                return model_usage
            
            for model_id in models:
                usage = ModelUsage()
                
                # Get invocation count
                usage.invocations = self._get_metric_sum(
                    'Invocations', model_id, start_time, end_time
                )
                
                # Get token counts
                usage.input_tokens = self._get_metric_sum(
                    'InputTokenCount', model_id, start_time, end_time
                )
                usage.output_tokens = self._get_metric_sum(
                    'OutputTokenCount', model_id, start_time, end_time
                )
                
                # Get latency data
                latency_sum = self._get_metric_sum(
                    'InvocationLatency', model_id, start_time, end_time
                )
                usage.total_latency = latency_sum / 1000.0  # Convert to seconds
                
                # Get error count from logs (with fallback)
                try:
                    usage.error_count = self._get_error_count(model_id, start_time, end_time)
                except Exception as e:
                    log_operation("GET_ERRORS", f"{model_id}", False, f"Error count unavailable: {str(e)}")
                    usage.error_count = 0
                
                if usage.invocations > 0:  # Only include models with actual usage
                    model_usage[model_id] = usage
            
        except Exception as e:
            log_operation("GET_METRICS", "CloudWatch", False, f"Failed to retrieve metrics: {str(e)}")
            # Return empty usage data rather than failing completely
        
        return model_usage
    
    def _get_available_models(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get list of models that have metrics in the time period."""
        try:
            response = self.cloudwatch.list_metrics(
                Namespace='AWS/Bedrock',
                MetricName='Invocations',
                StartTime=start_time,
                EndTime=end_time
            )
            
            models = set()
            for metric in response.get('Metrics', []):
                for dimension in metric.get('Dimensions', []):
                    if dimension['Name'] == 'ModelId':
                        models.add(dimension['Value'])
            
            return list(models)
        except ClientError as e:
            log_operation("GET_MODELS", "CloudWatch", False, str(e))
            return []
    
    def _get_metric_sum(self, metric_name: str, model_id: str, 
                       start_time: datetime, end_time: datetime) -> int:
        """Get sum of metric values for a specific model and time period."""
        try:
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Bedrock',
                MetricName=metric_name,
                Dimensions=[
                    {
                        'Name': 'ModelId',
                        'Value': model_id
                    }
                ],
                StartTime=start_time,
                EndTime=end_time,
                Period=3600,  # 1 hour periods
                Statistics=['Sum']
            )
            
            total = sum(point['Sum'] for point in response.get('Datapoints', []))
            return int(total)
        except ClientError as e:
            log_operation("GET_METRIC", f"{metric_name}:{model_id}", False, str(e))
            return 0
    
    def _get_error_count(self, model_id: str, start_time: datetime, end_time: datetime) -> int:
        """Get error count from CloudWatch logs."""
        try:
            # Query logs for errors related to this model
            query = f'''
            fields @timestamp, @message
            | filter @message like /ERROR/ or @message like /error/
            | filter @message like /{model_id}/
            | stats count() as error_count
            '''
            
            response = self.logs.start_query(
                logGroupName=self.config.storage.cloudwatch_log_group,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query
            )
            
            query_id = response['queryId']
            
            # Wait for query to complete with timeout
            import time
            max_wait = 10  # Maximum 10 seconds
            wait_time = 0
            
            while wait_time < max_wait:
                time.sleep(1)
                wait_time += 1
                
                try:
                    results = self.logs.get_query_results(queryId=query_id)
                    
                    if results['status'] == 'Complete':
                        if results['results']:
                            for result in results['results']:
                                for field in result:
                                    if field['field'] == 'error_count':
                                        return int(float(field['value']))
                        return 0
                    elif results['status'] == 'Failed':
                        log_operation("QUERY_LOGS", model_id, False, "Log query failed")
                        return 0
                except ClientError:
                    # Query may still be running
                    continue
            
            # Timeout reached
            log_operation("QUERY_LOGS", model_id, False, "Log query timeout")
            return 0
            
        except ClientError as e:
            # If logs are not available or query fails, return 0
            log_operation("QUERY_LOGS", model_id, False, f"Log query error: {str(e)}")
            return 0
        except Exception as e:
            log_operation("QUERY_LOGS", model_id, False, f"Unexpected error: {str(e)}")
            return 0
    
    def generate_report(self, hours: int) -> UsageReport:
        """Generate comprehensive usage report for the specified time period."""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)
        
        log_operation("GENERATE_REPORT", f"Period: {hours} hours", True, 
                     f"From {start_time.isoformat()} to {end_time.isoformat()}")
        
        # Get metrics data
        model_usage = self.get_metrics_data(start_time, end_time)
        
        # Calculate summary statistics
        total_invocations = sum(usage.invocations for usage in model_usage.values())
        total_input_tokens = sum(usage.input_tokens for usage in model_usage.values())
        total_output_tokens = sum(usage.output_tokens for usage in model_usage.values())
        total_cost = sum(
            BedrockPricing.calculate_cost(model_id, usage.input_tokens, usage.output_tokens)
            for model_id, usage in model_usage.items()
        )
        
        # Calculate performance statistics
        all_latencies = [usage.total_latency for usage in model_usage.values() if usage.invocations > 0]
        avg_latency = sum(usage.avg_latency * usage.invocations for usage in model_usage.values()) / total_invocations if total_invocations > 0 else 0
        total_errors = sum(usage.error_count for usage in model_usage.values())
        error_rate = (total_errors / total_invocations * 100) if total_invocations > 0 else 0
        
        # Calculate p99 latency (simplified approximation)
        p99_latency = max(all_latencies) if all_latencies else 0
        
        # Generate monthly projections
        hours_in_month = 24 * 30  # Approximate
        projection_multiplier = hours_in_month / hours if hours > 0 else 0
        
        monthly_invocations = int(total_invocations * projection_multiplier)
        monthly_cost = total_cost * projection_multiplier
        
        # Build by-model breakdown
        by_model = {}
        for model_id, usage in model_usage.items():
            cost = BedrockPricing.calculate_cost(model_id, usage.input_tokens, usage.output_tokens)
            by_model[model_id] = {
                'invocations': usage.invocations,
                'inputTokens': usage.input_tokens,
                'outputTokens': usage.output_tokens,
                'cost': round(cost, 4),
                'avgLatency': round(usage.avg_latency, 3),
                'errorCount': usage.error_count
            }
        
        # Create report structure
        report = UsageReport(
            period={
                'startTime': start_time.isoformat(),
                'endTime': end_time.isoformat(),
                'durationHours': hours
            },
            summary={
                'totalInvocations': total_invocations,
                'totalInputTokens': total_input_tokens,
                'totalOutputTokens': total_output_tokens,
                'estimatedCost': round(total_cost, 4)
            },
            by_model=by_model,
            projections={
                'monthlyInvocations': monthly_invocations,
                'monthlyCost': round(monthly_cost, 2)
            },
            performance={
                'avgLatency': round(avg_latency, 3),
                'p99Latency': round(p99_latency, 3),
                'errorCount': total_errors,
                'errorRate': round(error_rate, 2)
            }
        )
        
        return report
    
    def format_report(self, report: UsageReport, output_format: str = 'json') -> str:
        """Format report for output."""
        if output_format.lower() == 'json':
            return json.dumps(asdict(report), indent=2)
        
        elif output_format.lower() == 'text':
            return self._format_text_report(report)
        
        else:
            raise ValueError(f"Unsupported output format: {output_format}")
    
    def _format_text_report(self, report: UsageReport) -> str:
        """Format report as human-readable text."""
        lines = []
        lines.append("=" * 60)
        lines.append("AWS BEDROCK USAGE REPORT")
        lines.append("=" * 60)
        lines.append("")
        
        # Period information
        lines.append(f"Report Period: {report.period['durationHours']} hours")
        lines.append(f"From: {report.period['startTime']}")
        lines.append(f"To:   {report.period['endTime']}")
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 20)
        lines.append(f"Total Invocations:    {report.summary['totalInvocations']:,}")
        lines.append(f"Total Input Tokens:   {report.summary['totalInputTokens']:,}")
        lines.append(f"Total Output Tokens:  {report.summary['totalOutputTokens']:,}")
        lines.append(f"Estimated Cost:       ${report.summary['estimatedCost']:.4f}")
        lines.append("")
        
        # Performance
        lines.append("PERFORMANCE")
        lines.append("-" * 20)
        lines.append(f"Average Latency:      {report.performance['avgLatency']:.3f}s")
        lines.append(f"P99 Latency:          {report.performance['p99Latency']:.3f}s")
        lines.append(f"Error Count:          {report.performance['errorCount']}")
        lines.append(f"Error Rate:           {report.performance['errorRate']:.2f}%")
        lines.append("")
        
        # By model breakdown
        if report.by_model:
            lines.append("BY MODEL")
            lines.append("-" * 20)
            for model_id, usage in report.by_model.items():
                model_name = model_id.split('.')[-1] if '.' in model_id else model_id
                lines.append(f"\n{model_name}:")
                lines.append(f"  Invocations:     {usage['invocations']:,}")
                lines.append(f"  Input Tokens:    {usage['inputTokens']:,}")
                lines.append(f"  Output Tokens:   {usage['outputTokens']:,}")
                lines.append(f"  Cost:            ${usage['cost']:.4f}")
                lines.append(f"  Avg Latency:     {usage['avgLatency']:.3f}s")
                lines.append(f"  Errors:          {usage['errorCount']}")
        
        lines.append("")
        
        # Projections
        lines.append("MONTHLY PROJECTIONS")
        lines.append("-" * 20)
        lines.append(f"Projected Invocations: {report.projections['monthlyInvocations']:,}")
        lines.append(f"Projected Cost:        ${report.projections['monthlyCost']:.2f}")
        lines.append("")
        
        return "\n".join(lines)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Generate AWS Bedrock usage report with cost analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 6-usage-report.py --hours 24
  python3 6-usage-report.py --hours 168 --output text
  python3 6-usage-report.py --hours 72 --region us-west-2
        """
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Time period in hours for the report (default: 24)'
    )
    
    parser.add_argument(
        '--region',
        type=str,
        help='AWS region (default: from AWS config or us-east-1)'
    )
    
    parser.add_argument(
        '--output',
        choices=['json', 'text'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate parameters without generating report'
    )
    
    return parser.parse_args()


def validate_arguments(args: argparse.Namespace) -> List[str]:
    """Validate command line arguments."""
    errors = []
    
    # Validate hours
    if args.hours <= 0:
        errors.append("Hours must be a positive integer")
    elif args.hours > 8760:  # More than a year
        errors.append("Hours cannot exceed 8760 (1 year)")
    
    # Validate region if provided
    if args.region and not validate_aws_region(args.region):
        errors.append(f"Invalid AWS region format: {args.region}")
    
    return errors


def main():
    """Main entry point."""
    try:
        args = parse_arguments()
        
        # Validate arguments
        validation_errors = validate_arguments(args)
        if validation_errors:
            print("Validation errors:", file=sys.stderr)
            for error in validation_errors:
                print(f"  - {error}", file=sys.stderr)
            sys.exit(1)
        
        if args.validate_only:
            print("Arguments validation passed")
            return
        
        # Determine region
        region = args.region or get_aws_region() or 'us-east-1'
        
        # Generate report
        generator = UsageReportGenerator(region=region)
        report = generator.generate_report(args.hours)
        
        # Output report
        formatted_report = generator.format_report(report, args.output)
        print(formatted_report)
        
        log_operation("REPORT_COMPLETE", f"{args.hours}h report", True, 
                     f"Cost: ${report.summary['estimatedCost']:.4f}")
        
    except KeyboardInterrupt:
        print("\nReport generation cancelled by user", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()