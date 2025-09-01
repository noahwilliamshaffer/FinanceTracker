"""
Treasury Data Fetcher Lambda Function

This module implements the Lambda function responsible for fetching
treasury market data from external APIs, processing it into our
standardized format, and storing it in S3 with proper partitioning.
"""

import json
import boto3
import pandas as pd
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
import structlog
import os
import requests
from botocore.exceptions import ClientError

from ..models.treasury import TreasuryData, TreasuryPrice
from ..utils.s3_helper import S3DataManager
from ..utils.api_helper import APIClient
from ..utils.event_helper import EventPublisher

# Initialize structured logger for Lambda
logger = structlog.get_logger(__name__)


class TreasuryDataFetcher:
    """
    Fetches treasury market data from external APIs and processes it.
    
    This class handles the complete treasury data pipeline:
    1. Fetch data from external APIs (Treasury Direct, FRED, etc.)
    2. Transform data into standardized format using Pydantic models
    3. Store data in S3 with proper partitioning (year/month/day)
    4. Publish events to EventBridge for downstream processing
    5. Handle errors and data quality validation
    """
    
    def __init__(self):
        """Initialize the treasury data fetcher with AWS clients and configuration."""
        self.s3_manager = S3DataManager()
        self.event_publisher = EventPublisher()
        
        # Initialize API clients for different data sources
        self.treasury_direct_client = APIClient(
            base_url="https://api.fiscaldata.treasury.gov/services/api/v1",
            rate_limit_per_hour=1000
        )
        
        self.fred_client = APIClient(
            base_url="https://api.stlouisfed.org/fred",
            rate_limit_per_day=12000,
            api_key_secret="finance-tracker/fred-api-key"
        )
        
        # Configuration from environment variables
        self.s3_bucket = os.environ.get('S3_BUCKET', 'finance-tracker-data-783085491860')
        self.log_level = os.environ.get('LOG_LEVEL', 'INFO')
        
        # Configure logging level
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger(
                getattr(structlog.stdlib.LogLevel, self.log_level)
            )
        )
        
        logger.info(
            "TreasuryDataFetcher initialized",
            s3_bucket=self.s3_bucket,
            log_level=self.log_level
        )
    
    def fetch_treasury_securities_list(self) -> List[Dict[str, Any]]:
        """
        Fetch the list of active treasury securities from Treasury Direct API.
        
        Returns:
            List[Dict]: List of treasury security metadata
            
        Raises:
            APIError: If the API request fails
            DataValidationError: If the response data is invalid
        """
        logger.info("Fetching treasury securities list from Treasury Direct API")
        
        try:
            # Fetch active treasury securities
            response = self.treasury_direct_client.get(
                "/accounting/od/debt_to_penny",
                params={
                    "filter": "record_date:gte:2024-01-01",
                    "fields": "record_date,debt_held_public_amt,intragov_hold_amt",
                    "format": "json",
                    "page[size]": "1000"
                }
            )
            
            securities_data = response.get('data', [])
            
            logger.info(
                "Successfully fetched treasury securities",
                count=len(securities_data)
            )
            
            return securities_data
            
        except requests.RequestException as e:
            logger.error(
                "Failed to fetch treasury securities from API",
                error=str(e),
                api="treasury_direct"
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error fetching treasury securities",
                error=str(e)
            )
            raise
    
    def fetch_treasury_prices(self, cusips: List[str]) -> Dict[str, TreasuryPrice]:
        """
        Fetch current treasury prices for specified CUSIPs.
        
        Args:
            cusips: List of CUSIP identifiers to fetch prices for
            
        Returns:
            Dict[str, TreasuryPrice]: Mapping of CUSIP to price data
        """
        logger.info(
            "Fetching treasury prices",
            cusip_count=len(cusips)
        )
        
        price_data = {}
        
        for cusip in cusips:
            try:
                # In a real implementation, this would call actual pricing APIs
                # For now, we'll simulate with sample data structure
                
                # Fetch BVAL prices (Bloomberg Valuation Service)
                bval_price = self._fetch_bval_price(cusip)
                
                # Fetch internal pricing model results
                internal_price = self._fetch_internal_price(cusip)
                
                # Calculate day-over-day change
                previous_price = self._fetch_previous_price(cusip)
                day_change = None
                if previous_price and bval_price:
                    day_change = bval_price - previous_price
                
                # Create TreasuryPrice object with validation
                price_record = TreasuryPrice(
                    cusip=cusip,
                    price_date=date.today(),
                    bval_price=bval_price,
                    internal_price=internal_price,
                    day_over_day_change=day_change
                )
                
                price_data[cusip] = price_record
                
                logger.debug(
                    "Fetched price data for CUSIP",
                    cusip=cusip,
                    bval_price=float(bval_price) if bval_price else None,
                    internal_price=float(internal_price) if internal_price else None
                )
                
            except Exception as e:
                logger.warning(
                    "Failed to fetch price data for CUSIP",
                    cusip=cusip,
                    error=str(e)
                )
                continue
        
        logger.info(
            "Treasury price fetching completed",
            successful_cusips=len(price_data),
            total_cusips=len(cusips)
        )
        
        return price_data
    
    def _fetch_bval_price(self, cusip: str) -> Optional[Decimal]:
        """
        Fetch BVAL (Bloomberg Valuation) price for a CUSIP.
        
        In production, this would integrate with Bloomberg API or
        other market data providers.
        """
        try:
            # Placeholder for actual BVAL API integration
            # This would typically require Bloomberg Terminal API or similar
            
            # For demo purposes, simulate realistic treasury prices
            base_price = Decimal('99.50')  # Typical treasury price near par
            
            # Add some realistic variation based on CUSIP
            cusip_hash = hash(cusip) % 1000
            variation = Decimal(str(cusip_hash / 10000))  # Small price variations
            
            return base_price + variation
            
        except Exception as e:
            logger.warning(
                "Failed to fetch BVAL price",
                cusip=cusip,
                error=str(e)
            )
            return None
    
    def _fetch_internal_price(self, cusip: str) -> Optional[Decimal]:
        """
        Fetch internal pricing model result for a CUSIP.
        
        This would typically call internal pricing models or
        retrieve cached model results from a database.
        """
        try:
            # Placeholder for internal pricing model
            # In practice, this might call a separate microservice
            # or retrieve results from a pricing database
            
            # Simulate internal model that's slightly different from BVAL
            base_price = Decimal('99.45')  # Slightly different from BVAL
            
            cusip_hash = hash(cusip + "internal") % 1000
            variation = Decimal(str(cusip_hash / 8000))
            
            return base_price + variation
            
        except Exception as e:
            logger.warning(
                "Failed to fetch internal price",
                cusip=cusip,
                error=str(e)
            )
            return None
    
    def _fetch_previous_price(self, cusip: str) -> Optional[Decimal]:
        """
        Fetch previous day's price for day-over-day change calculation.
        
        This would typically query the S3 data lake or a time series database.
        """
        try:
            # In production, this would query yesterday's data from S3
            # For now, simulate a previous price slightly lower
            current_price = self._fetch_bval_price(cusip)
            if current_price:
                return current_price - Decimal('0.05')  # Simulate small daily change
            return None
            
        except Exception as e:
            logger.warning(
                "Failed to fetch previous price",
                cusip=cusip,
                error=str(e)
            )
            return None
    
    def process_and_store_data(
        self, 
        price_data: Dict[str, TreasuryPrice]
    ) -> Dict[str, Any]:
        """
        Process treasury price data and store in S3 with proper partitioning.
        
        Args:
            price_data: Dictionary mapping CUSIP to TreasuryPrice objects
            
        Returns:
            Dict: Processing results including file locations and metrics
        """
        logger.info(
            "Processing and storing treasury data",
            record_count=len(price_data)
        )
        
        processing_results = {
            'processed_count': 0,
            'failed_count': 0,
            's3_locations': [],
            'processing_errors': []
        }
        
        try:
            # Convert to DataFrame for easier manipulation
            records = []
            for cusip, price_record in price_data.items():
                try:
                    # Convert Pydantic model to dict for DataFrame
                    record_dict = price_record.dict()
                    record_dict['cusip'] = cusip
                    records.append(record_dict)
                    processing_results['processed_count'] += 1
                    
                except Exception as e:
                    logger.warning(
                        "Failed to process price record",
                        cusip=cusip,
                        error=str(e)
                    )
                    processing_results['failed_count'] += 1
                    processing_results['processing_errors'].append({
                        'cusip': cusip,
                        'error': str(e)
                    })
            
            if not records:
                logger.warning("No valid records to store")
                return processing_results
            
            # Create DataFrame and add metadata
            df = pd.DataFrame(records)
            df['processing_timestamp'] = datetime.utcnow().isoformat()
            df['data_source'] = 'treasury_fetcher'
            
            # Store data in S3 with date partitioning
            today = date.today()
            s3_key = f"treasury/year={today.year}/month={today.month:02d}/day={today.day:02d}/treasury_prices_{datetime.utcnow().strftime('%H%M%S')}.csv"
            
            s3_location = self.s3_manager.store_dataframe(
                df=df,
                bucket=self.s3_bucket,
                key=s3_key,
                file_format='csv'
            )
            
            processing_results['s3_locations'].append(s3_location)
            
            # Create manifest file for audit trail
            manifest_data = {
                'file_location': s3_location,
                'record_count': len(records),
                'processing_timestamp': datetime.utcnow().isoformat(),
                'data_schema_version': '1.0',
                'cusips_processed': list(price_data.keys())
            }
            
            manifest_key = f"treasury/manifests/year={today.year}/month={today.month:02d}/day={today.day:02d}/manifest_{datetime.utcnow().strftime('%H%M%S')}.json"
            
            manifest_location = self.s3_manager.store_json(
                data=manifest_data,
                bucket=self.s3_bucket,
                key=manifest_key
            )
            
            processing_results['manifest_location'] = manifest_location
            
            logger.info(
                "Treasury data successfully stored",
                s3_location=s3_location,
                manifest_location=manifest_location,
                record_count=len(records)
            )
            
        except Exception as e:
            logger.error(
                "Failed to process and store treasury data",
                error=str(e)
            )
            processing_results['processing_errors'].append({
                'error': str(e),
                'stage': 'data_storage'
            })
        
        return processing_results
    
    def publish_completion_event(self, processing_results: Dict[str, Any]):
        """
        Publish EventBridge event indicating treasury data processing completion.
        
        Args:
            processing_results: Results from data processing including metrics
        """
        try:
            event_detail = {
                'source': 'finance.treasury',
                'detail-type': 'Treasury Data Update',
                'detail': {
                    'status': 'success' if processing_results['failed_count'] == 0 else 'partial',
                    'processed_count': processing_results['processed_count'],
                    'failed_count': processing_results['failed_count'],
                    's3_locations': processing_results['s3_locations'],
                    'processing_timestamp': datetime.utcnow().isoformat(),
                    'data_freshness_minutes': 0  # Just processed
                }
            }
            
            self.event_publisher.publish_event(event_detail)
            
            logger.info(
                "Treasury data completion event published",
                status=event_detail['detail']['status'],
                processed_count=processing_results['processed_count']
            )
            
        except Exception as e:
            logger.error(
                "Failed to publish completion event",
                error=str(e)
            )


def lambda_handler(event: Dict[str, Any], context) -> Dict[str, Any]:
    """
    AWS Lambda handler for treasury data fetching.
    
    This function is triggered by EventBridge on a schedule or by
    manual invocation. It orchestrates the complete treasury data
    fetching and processing pipeline.
    
    Args:
        event: Lambda event data (EventBridge event or manual trigger)
        context: Lambda runtime context
        
    Returns:
        Dict: Processing results and status information
    """
    logger.info(
        "Treasury data fetcher Lambda started",
        event_source=event.get('source', 'manual'),
        request_id=context.aws_request_id if context else 'local'
    )
    
    fetcher = TreasuryDataFetcher()
    
    try:
        # Extract configuration from event if provided
        cusips_to_fetch = event.get('detail', {}).get('cusips', [])
        
        # If no specific CUSIPs provided, fetch common treasury securities
        if not cusips_to_fetch:
            cusips_to_fetch = [
                "912828XG8",  # 10-Year Treasury Note
                "912828YK0",  # 2-Year Treasury Note  
                "912810RZ3",  # 30-Year Treasury Bond
                "912828YH7",  # 5-Year Treasury Note
                "912828YM4",  # 3-Year Treasury Note
            ]
        
        logger.info(
            "Starting treasury data fetch",
            cusip_count=len(cusips_to_fetch)
        )
        
        # Step 1: Fetch price data for specified CUSIPs
        price_data = fetcher.fetch_treasury_prices(cusips_to_fetch)
        
        # Step 2: Process and store data in S3
        processing_results = fetcher.process_and_store_data(price_data)
        
        # Step 3: Publish completion event for downstream processing
        fetcher.publish_completion_event(processing_results)
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': {
                'message': 'Treasury data fetch completed successfully',
                'processed_count': processing_results['processed_count'],
                'failed_count': processing_results['failed_count'],
                's3_locations': processing_results['s3_locations'],
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        }
        
        logger.info(
            "Treasury data fetcher completed successfully",
            processed_count=processing_results['processed_count'],
            failed_count=processing_results['failed_count']
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Treasury data fetcher failed",
            error=str(e),
            request_id=context.aws_request_id if context else 'local'
        )
        
        # Publish failure event
        try:
            failure_event = {
                'source': 'finance.treasury',
                'detail-type': 'Treasury Data Update Failure',
                'detail': {
                    'status': 'failed',
                    'error': str(e),
                    'processing_timestamp': datetime.utcnow().isoformat()
                }
            }
            fetcher.event_publisher.publish_event(failure_event)
        except:
            pass  # Don't fail on event publishing failure
        
        return {
            'statusCode': 500,
            'body': {
                'message': 'Treasury data fetch failed',
                'error': str(e),
                'processing_timestamp': datetime.utcnow().isoformat()
            }
        }
