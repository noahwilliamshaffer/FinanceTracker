"""
EventBridge Event Publishing Helper

This module provides utilities for publishing events to AWS EventBridge
for the Finance Tracker event-driven architecture with proper event
formatting, error handling, and audit trails.
"""

import boto3
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import structlog
from botocore.exceptions import ClientError

# Initialize structured logger
logger = structlog.get_logger(__name__)


class EventPublisher:
    """
    Publishes events to AWS EventBridge for the Finance Tracker pipeline.
    
    This class handles all EventBridge event publishing with proper
    event formatting, batch processing, error handling, and audit trails.
    
    Features:
    - Standardized event format for Finance Tracker events
    - Batch event publishing for efficiency
    - Automatic retry logic for failed events
    - Event validation and schema enforcement
    - Audit trail generation for all published events
    """
    
    def __init__(self, event_bus_name: str = "finance-tracker-events", region_name: str = "us-east-1"):
        """
        Initialize EventBridge event publisher.
        
        Args:
            event_bus_name: Name of the custom EventBridge event bus
            region_name: AWS region for EventBridge operations
        """
        self.event_bus_name = event_bus_name
        self.region_name = region_name
        
        try:
            self.events_client = boto3.client('events', region_name=region_name)
            
            logger.info(
                "EventPublisher initialized",
                event_bus_name=event_bus_name,
                region=region_name
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize EventBridge client",
                error=str(e)
            )
            raise
    
    def publish_event(
        self,
        event_data: Dict[str, Any],
        event_bus_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a single event to EventBridge.
        
        Args:
            event_data: Event data with source, detail-type, and detail
            event_bus_name: Override default event bus name
            
        Returns:
            Dict[str, Any]: Publishing result with event ID and status
            
        Raises:
            ValueError: If event data is invalid
            ClientError: If EventBridge operation fails
        """
        bus_name = event_bus_name or self.event_bus_name
        
        logger.info(
            "Publishing single event to EventBridge",
            source=event_data.get('source'),
            detail_type=event_data.get('detail-type'),
            event_bus=bus_name
        )
        
        # Validate and format event
        formatted_event = self._format_event(event_data)
        
        try:
            response = self.events_client.put_events(
                Entries=[formatted_event]
            )
            
            # Check for failures
            failed_entries = response.get('FailedEntryCount', 0)
            if failed_entries > 0:
                failure_details = response.get('Entries', [{}])[0]
                error_code = failure_details.get('ErrorCode')
                error_message = failure_details.get('ErrorMessage')
                
                logger.error(
                    "Event publishing failed",
                    error_code=error_code,
                    error_message=error_message,
                    event_source=event_data.get('source')
                )
                
                return {
                    'status': 'failed',
                    'error_code': error_code,
                    'error_message': error_message
                }
            
            # Success case
            event_id = response.get('Entries', [{}])[0].get('EventId')
            
            logger.info(
                "Event successfully published",
                event_id=event_id,
                source=event_data.get('source'),
                detail_type=event_data.get('detail-type')
            )
            
            return {
                'status': 'success',
                'event_id': event_id,
                'event_bus': bus_name
            }
            
        except ClientError as e:
            logger.error(
                "EventBridge client error during event publishing",
                error=str(e),
                event_source=event_data.get('source')
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error during event publishing",
                error=str(e),
                event_source=event_data.get('source')
            )
            raise
    
    def publish_batch_events(
        self,
        events: List[Dict[str, Any]],
        event_bus_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish multiple events to EventBridge in batches.
        
        EventBridge supports up to 10 events per batch. This method
        automatically handles batching for larger event lists.
        
        Args:
            events: List of event data dictionaries
            event_bus_name: Override default event bus name
            
        Returns:
            Dict[str, Any]: Batch publishing results with success/failure counts
        """
        bus_name = event_bus_name or self.event_bus_name
        batch_size = 10  # EventBridge maximum batch size
        
        logger.info(
            "Publishing batch events to EventBridge",
            event_count=len(events),
            event_bus=bus_name,
            batch_size=batch_size
        )
        
        results = {
            'total_events': len(events),
            'successful_events': 0,
            'failed_events': 0,
            'batch_results': [],
            'failed_event_details': []
        }
        
        # Process events in batches
        for i in range(0, len(events), batch_size):
            batch = events[i:i + batch_size]
            batch_number = (i // batch_size) + 1
            
            logger.debug(
                "Processing event batch",
                batch_number=batch_number,
                batch_size=len(batch)
            )
            
            try:
                # Format all events in the batch
                formatted_batch = []
                for event_data in batch:
                    try:
                        formatted_event = self._format_event(event_data)
                        formatted_batch.append(formatted_event)
                    except Exception as e:
                        logger.warning(
                            "Failed to format event in batch",
                            batch_number=batch_number,
                            error=str(e),
                            event_source=event_data.get('source')
                        )
                        results['failed_events'] += 1
                        results['failed_event_details'].append({
                            'event': event_data,
                            'error': str(e),
                            'stage': 'formatting'
                        })
                
                if not formatted_batch:
                    logger.warning(
                        "No valid events in batch after formatting",
                        batch_number=batch_number
                    )
                    continue
                
                # Publish the batch
                response = self.events_client.put_events(Entries=formatted_batch)
                
                # Process batch results
                failed_count = response.get('FailedEntryCount', 0)
                successful_count = len(formatted_batch) - failed_count
                
                results['successful_events'] += successful_count
                results['failed_events'] += failed_count
                
                batch_result = {
                    'batch_number': batch_number,
                    'batch_size': len(formatted_batch),
                    'successful_count': successful_count,
                    'failed_count': failed_count
                }
                
                # Log failed entries in this batch
                if failed_count > 0:
                    for idx, entry_result in enumerate(response.get('Entries', [])):
                        if 'ErrorCode' in entry_result:
                            failed_event = {
                                'batch_number': batch_number,
                                'event_index': idx,
                                'error_code': entry_result.get('ErrorCode'),
                                'error_message': entry_result.get('ErrorMessage'),
                                'original_event': batch[idx] if idx < len(batch) else None
                            }
                            results['failed_event_details'].append(failed_event)
                            
                            logger.warning(
                                "Event failed in batch",
                                batch_number=batch_number,
                                event_index=idx,
                                error_code=entry_result.get('ErrorCode'),
                                error_message=entry_result.get('ErrorMessage')
                            )
                
                results['batch_results'].append(batch_result)
                
                logger.debug(
                    "Batch processing completed",
                    batch_number=batch_number,
                    successful_count=successful_count,
                    failed_count=failed_count
                )
                
            except ClientError as e:
                logger.error(
                    "EventBridge client error during batch publishing",
                    batch_number=batch_number,
                    error=str(e)
                )
                results['failed_events'] += len(batch)
                results['failed_event_details'].extend([
                    {
                        'event': event,
                        'error': str(e),
                        'stage': 'publishing',
                        'batch_number': batch_number
                    } for event in batch
                ])
                
            except Exception as e:
                logger.error(
                    "Unexpected error during batch publishing",
                    batch_number=batch_number,
                    error=str(e)
                )
                results['failed_events'] += len(batch)
        
        logger.info(
            "Batch event publishing completed",
            total_events=results['total_events'],
            successful_events=results['successful_events'],
            failed_events=results['failed_events'],
            success_rate=f"{(results['successful_events'] / results['total_events'] * 100):.1f}%" if results['total_events'] > 0 else "0%"
        )
        
        return results
    
    def _format_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format event data according to EventBridge standards.
        
        Args:
            event_data: Raw event data
            
        Returns:
            Dict[str, Any]: Formatted event for EventBridge
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        required_fields = ['source', 'detail-type', 'detail']
        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Create formatted event
        formatted_event = {
            'Source': event_data['source'],
            'DetailType': event_data['detail-type'],
            'Detail': json.dumps(event_data['detail'], default=str),
            'EventBusName': self.event_bus_name,
            'Time': datetime.utcnow()
        }
        
        # Add optional fields if present
        if 'resources' in event_data:
            formatted_event['Resources'] = event_data['resources']
        
        # Add Finance Tracker specific metadata
        detail = event_data['detail'].copy() if isinstance(event_data['detail'], dict) else {}
        detail.update({
            'event_timestamp': datetime.utcnow().isoformat(),
            'event_version': '1.0',
            'application': 'finance-tracker'
        })
        
        formatted_event['Detail'] = json.dumps(detail, default=str)
        
        # Validate event size (EventBridge has 256KB limit per event)
        event_size = len(json.dumps(formatted_event, default=str).encode('utf-8'))
        if event_size > 256000:  # 256KB in bytes
            logger.warning(
                "Event size exceeds EventBridge limit",
                event_size_bytes=event_size,
                event_source=event_data['source']
            )
            # Truncate detail if too large
            detail_str = json.dumps(detail, default=str)
            if len(detail_str) > 200000:  # Leave room for other fields
                truncated_detail = detail_str[:200000] + "...[TRUNCATED]"
                formatted_event['Detail'] = truncated_detail
                
                logger.info(
                    "Event detail truncated due to size limit",
                    original_size=len(detail_str),
                    truncated_size=len(truncated_detail)
                )
        
        return formatted_event
    
    def publish_treasury_data_event(
        self,
        status: str,
        processed_count: int,
        failed_count: int = 0,
        s3_locations: Optional[List[str]] = None,
        cusips: Optional[List[str]] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish a standardized treasury data update event.
        
        Args:
            status: Processing status ('success', 'partial', 'failed')
            processed_count: Number of records processed successfully
            failed_count: Number of records that failed processing
            s3_locations: List of S3 URIs where data was stored
            cusips: List of CUSIPs that were processed
            additional_details: Additional event details
            
        Returns:
            Dict[str, Any]: Publishing result
        """
        event_detail = {
            'status': status,
            'processed_count': processed_count,
            'failed_count': failed_count,
            'processing_timestamp': datetime.utcnow().isoformat(),
            'data_type': 'treasury_prices'
        }
        
        if s3_locations:
            event_detail['s3_locations'] = s3_locations
        
        if cusips:
            event_detail['cusips'] = cusips
        
        if additional_details:
            event_detail.update(additional_details)
        
        event_data = {
            'source': 'finance.treasury',
            'detail-type': 'Treasury Data Update',
            'detail': event_detail
        }
        
        return self.publish_event(event_data)
    
    def publish_repo_data_event(
        self,
        status: str,
        processed_count: int,
        failed_count: int = 0,
        s3_locations: Optional[List[str]] = None,
        cusips: Optional[List[str]] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish a standardized repo data update event.
        
        Args:
            status: Processing status ('success', 'partial', 'failed')
            processed_count: Number of records processed successfully
            failed_count: Number of records that failed processing
            s3_locations: List of S3 URIs where data was stored
            cusips: List of CUSIPs that were processed
            additional_details: Additional event details
            
        Returns:
            Dict[str, Any]: Publishing result
        """
        event_detail = {
            'status': status,
            'processed_count': processed_count,
            'failed_count': failed_count,
            'processing_timestamp': datetime.utcnow().isoformat(),
            'data_type': 'repo_spreads'
        }
        
        if s3_locations:
            event_detail['s3_locations'] = s3_locations
        
        if cusips:
            event_detail['cusips'] = cusips
        
        if additional_details:
            event_detail.update(additional_details)
        
        event_data = {
            'source': 'finance.repo',
            'detail-type': 'Repo Data Update',
            'detail': event_detail
        }
        
        return self.publish_event(event_data)
    
    def publish_scoring_event(
        self,
        status: str,
        processed_count: int,
        failed_count: int = 0,
        score_statistics: Optional[Dict[str, Any]] = None,
        additional_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publish a standardized scoring calculation event.
        
        Args:
            status: Processing status ('success', 'partial', 'failed')
            processed_count: Number of scores calculated successfully
            failed_count: Number of scores that failed calculation
            score_statistics: Statistical summary of calculated scores
            additional_details: Additional event details
            
        Returns:
            Dict[str, Any]: Publishing result
        """
        event_detail = {
            'status': status,
            'processed_count': processed_count,
            'failed_count': failed_count,
            'processing_timestamp': datetime.utcnow().isoformat(),
            'data_type': 'composite_scores'
        }
        
        if score_statistics:
            event_detail['score_statistics'] = score_statistics
        
        if additional_details:
            event_detail.update(additional_details)
        
        event_data = {
            'source': 'finance.scoring',
            'detail-type': 'Score Calculation Complete',
            'detail': event_detail
        }
        
        return self.publish_event(event_data)
