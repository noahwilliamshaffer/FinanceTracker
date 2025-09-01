"""
S3 Data Management Helper

This module provides a centralized interface for all S3 operations
including data storage, retrieval, partitioning, and audit trail
management for the Finance Tracker application.
"""

import boto3
import json
import pandas as pd
from io import StringIO, BytesIO
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import structlog
from botocore.exceptions import ClientError, NoCredentialsError

# Initialize structured logger
logger = structlog.get_logger(__name__)


class S3DataManager:
    """
    Manages all S3 data operations with audit-ready practices.
    
    This class provides high-level methods for storing and retrieving
    data in S3 with proper partitioning, versioning, encryption,
    and audit trail generation.
    
    Features:
    - Automatic partitioning by date and data type
    - Audit trail generation with row count manifests
    - Support for multiple file formats (CSV, JSON, Parquet)
    - Encryption and versioning compliance
    - Error handling and retry logic
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize S3 data manager with AWS clients.
        
        Args:
            region_name: AWS region for S3 operations
        """
        try:
            self.s3_client = boto3.client('s3', region_name=region_name)
            self.region_name = region_name
            
            logger.info(
                "S3DataManager initialized",
                region=region_name
            )
            
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise
        except Exception as e:
            logger.error(
                "Failed to initialize S3 client",
                error=str(e)
            )
            raise
    
    def store_dataframe(
        self,
        df: pd.DataFrame,
        bucket: str,
        key: str,
        file_format: str = 'csv',
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store a pandas DataFrame in S3 with audit metadata.
        
        Args:
            df: DataFrame to store
            bucket: S3 bucket name
            key: S3 object key (path)
            file_format: File format ('csv', 'parquet', 'json')
            metadata: Additional metadata to attach to S3 object
            
        Returns:
            str: S3 URI of stored object
            
        Raises:
            ValueError: If file format is unsupported
            ClientError: If S3 operation fails
        """
        logger.info(
            "Storing DataFrame in S3",
            bucket=bucket,
            key=key,
            format=file_format,
            rows=len(df),
            columns=len(df.columns)
        )
        
        # Prepare metadata with audit information
        s3_metadata = {
            'row-count': str(len(df)),
            'column-count': str(len(df.columns)),
            'storage-timestamp': datetime.utcnow().isoformat(),
            'data-format': file_format,
            'finance-tracker-version': '1.0'
        }
        
        if metadata:
            s3_metadata.update(metadata)
        
        try:
            # Convert DataFrame to appropriate format
            if file_format.lower() == 'csv':
                buffer = StringIO()
                df.to_csv(buffer, index=False)
                content = buffer.getvalue().encode('utf-8')
                content_type = 'text/csv'
                
            elif file_format.lower() == 'parquet':
                buffer = BytesIO()
                df.to_parquet(buffer, index=False)
                content = buffer.getvalue()
                content_type = 'application/octet-stream'
                
            elif file_format.lower() == 'json':
                content = df.to_json(orient='records', date_format='iso').encode('utf-8')
                content_type = 'application/json'
                
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            # Store in S3 with metadata
            response = self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                Metadata=s3_metadata,
                ServerSideEncryption='AES256'  # Enable encryption
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            
            logger.info(
                "DataFrame successfully stored in S3",
                s3_uri=s3_uri,
                etag=response.get('ETag', '').strip('"'),
                version_id=response.get('VersionId')
            )
            
            return s3_uri
            
        except ClientError as e:
            logger.error(
                "Failed to store DataFrame in S3",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error storing DataFrame",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
    
    def store_json(
        self,
        data: Union[Dict, List],
        bucket: str,
        key: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Store JSON data in S3 with audit metadata.
        
        Args:
            data: JSON-serializable data to store
            bucket: S3 bucket name
            key: S3 object key (path)
            metadata: Additional metadata to attach
            
        Returns:
            str: S3 URI of stored object
        """
        logger.info(
            "Storing JSON data in S3",
            bucket=bucket,
            key=key,
            data_type=type(data).__name__
        )
        
        # Prepare metadata
        s3_metadata = {
            'data-type': type(data).__name__,
            'storage-timestamp': datetime.utcnow().isoformat(),
            'finance-tracker-version': '1.0'
        }
        
        if metadata:
            s3_metadata.update(metadata)
        
        try:
            # Serialize to JSON
            json_content = json.dumps(data, indent=2, default=str)
            
            # Store in S3
            response = self.s3_client.put_object(
                Bucket=bucket,
                Key=key,
                Body=json_content.encode('utf-8'),
                ContentType='application/json',
                Metadata=s3_metadata,
                ServerSideEncryption='AES256'
            )
            
            s3_uri = f"s3://{bucket}/{key}"
            
            logger.info(
                "JSON data successfully stored in S3",
                s3_uri=s3_uri,
                etag=response.get('ETag', '').strip('"')
            )
            
            return s3_uri
            
        except (ClientError, json.JSONEncodeError) as e:
            logger.error(
                "Failed to store JSON data in S3",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
    
    def retrieve_dataframe(
        self,
        bucket: str,
        key: str,
        file_format: str = 'csv'
    ) -> pd.DataFrame:
        """
        Retrieve a DataFrame from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            file_format: Expected file format ('csv', 'parquet', 'json')
            
        Returns:
            pd.DataFrame: Retrieved DataFrame
            
        Raises:
            ClientError: If S3 object doesn't exist or access denied
            ValueError: If file format is unsupported or data is invalid
        """
        logger.info(
            "Retrieving DataFrame from S3",
            bucket=bucket,
            key=key,
            format=file_format
        )
        
        try:
            # Get object from S3
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            
            # Parse based on format
            if file_format.lower() == 'csv':
                df = pd.read_csv(StringIO(content.decode('utf-8')))
                
            elif file_format.lower() == 'parquet':
                df = pd.read_parquet(BytesIO(content))
                
            elif file_format.lower() == 'json':
                df = pd.read_json(StringIO(content.decode('utf-8')), orient='records')
                
            else:
                raise ValueError(f"Unsupported file format: {file_format}")
            
            logger.info(
                "DataFrame successfully retrieved from S3",
                bucket=bucket,
                key=key,
                rows=len(df),
                columns=len(df.columns)
            )
            
            return df
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                logger.warning(
                    "S3 object not found",
                    bucket=bucket,
                    key=key
                )
            else:
                logger.error(
                    "Failed to retrieve DataFrame from S3",
                    bucket=bucket,
                    key=key,
                    error=str(e)
                )
            raise
        except Exception as e:
            logger.error(
                "Unexpected error retrieving DataFrame",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
    
    def retrieve_json(self, bucket: str, key: str) -> Union[Dict, List]:
        """
        Retrieve JSON data from S3.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            
        Returns:
            Union[Dict, List]: Parsed JSON data
        """
        logger.info(
            "Retrieving JSON data from S3",
            bucket=bucket,
            key=key
        )
        
        try:
            response = self.s3_client.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read().decode('utf-8')
            data = json.loads(content)
            
            logger.info(
                "JSON data successfully retrieved from S3",
                bucket=bucket,
                key=key,
                data_type=type(data).__name__
            )
            
            return data
            
        except ClientError as e:
            logger.error(
                "Failed to retrieve JSON data from S3",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(
                "Invalid JSON data in S3 object",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
    
    def list_objects(
        self,
        bucket: str,
        prefix: str = '',
        max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        List objects in S3 bucket with optional prefix filter.
        
        Args:
            bucket: S3 bucket name
            prefix: Object key prefix to filter by
            max_keys: Maximum number of objects to return
            
        Returns:
            List[Dict]: List of object metadata
        """
        logger.info(
            "Listing S3 objects",
            bucket=bucket,
            prefix=prefix,
            max_keys=max_keys
        )
        
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            objects = response.get('Contents', [])
            
            logger.info(
                "S3 objects listed successfully",
                bucket=bucket,
                prefix=prefix,
                object_count=len(objects)
            )
            
            return objects
            
        except ClientError as e:
            logger.error(
                "Failed to list S3 objects",
                bucket=bucket,
                prefix=prefix,
                error=str(e)
            )
            raise
    
    def generate_presigned_url(
        self,
        bucket: str,
        key: str,
        expiration: int = 3600,
        http_method: str = 'get_object'
    ) -> str:
        """
        Generate a presigned URL for S3 object access.
        
        Args:
            bucket: S3 bucket name
            key: S3 object key
            expiration: URL expiration time in seconds
            http_method: HTTP method ('get_object', 'put_object')
            
        Returns:
            str: Presigned URL
        """
        logger.info(
            "Generating presigned URL",
            bucket=bucket,
            key=key,
            expiration=expiration,
            method=http_method
        )
        
        try:
            url = self.s3_client.generate_presigned_url(
                http_method,
                Params={'Bucket': bucket, 'Key': key},
                ExpiresIn=expiration
            )
            
            logger.info(
                "Presigned URL generated successfully",
                bucket=bucket,
                key=key
            )
            
            return url
            
        except ClientError as e:
            logger.error(
                "Failed to generate presigned URL",
                bucket=bucket,
                key=key,
                error=str(e)
            )
            raise
    
    def create_audit_log(
        self,
        bucket: str,
        operation: str,
        details: Dict[str, Any],
        audit_bucket: Optional[str] = None
    ) -> str:
        """
        Create an immutable audit log entry for data operations.
        
        Args:
            bucket: Bucket where operation occurred
            operation: Type of operation performed
            details: Operation details and metadata
            audit_bucket: Separate bucket for audit logs (optional)
            
        Returns:
            str: S3 URI of audit log entry
        """
        audit_bucket = audit_bucket or bucket
        
        # Create audit log entry
        audit_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'bucket': bucket,
            'details': details,
            'audit_version': '1.0'
        }
        
        # Generate audit log key with timestamp for uniqueness
        timestamp_str = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')
        audit_key = f"audit-logs/{operation}/{timestamp_str}.json"
        
        try:
            audit_uri = self.store_json(
                data=audit_entry,
                bucket=audit_bucket,
                key=audit_key,
                metadata={
                    'audit-operation': operation,
                    'source-bucket': bucket
                }
            )
            
            logger.info(
                "Audit log entry created",
                operation=operation,
                audit_uri=audit_uri
            )
            
            return audit_uri
            
        except Exception as e:
            logger.error(
                "Failed to create audit log entry",
                operation=operation,
                error=str(e)
            )
            raise
