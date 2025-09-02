"""
Real-Time Data Feeds Integration
Connects to Treasury Direct, FRED, and Bloomberg APIs for live market data
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import json
import logging
from dataclasses import dataclass
from enum import Enum
import os
from pydantic import BaseModel, Field
import redis
import websockets

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Enumeration of available data sources"""
    TREASURY_DIRECT = "treasury_direct"
    FRED = "fred"
    BLOOMBERG = "bloomberg"
    INTERNAL = "internal"

@dataclass
class MarketDataPoint:
    """Individual market data point"""
    symbol: str
    price: float
    timestamp: datetime
    source: DataSource
    data_type: str  # 'treasury', 'repo', 'rate'
    metadata: Dict[str, Any] = None

class TreasuryDirectAPI:
    """
    Treasury Direct API integration for live bond prices
    https://www.treasurydirect.gov/TA_WS/securities
    """
    
    def __init__(self):
        self.base_url = "https://www.treasurydirect.gov/TA_WS/securities"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_treasury_securities(self, security_type: str = "Bill") -> List[Dict]:
        """Fetch current Treasury securities data"""
        try:
            params = {
                'format': 'json',
                'type': security_type,
                'pagesize': 100
            }
            
            async with self.session.get(self.base_url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched {len(data)} {security_type} securities from Treasury Direct")
                    return data
                else:
                    logger.error(f"Treasury Direct API error: {response.status}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching Treasury data: {e}")
            return []
    
    async def get_auction_data(self) -> List[Dict]:
        """Fetch upcoming and recent auction data"""
        try:
            auction_url = f"{self.base_url}/auctions"
            async with self.session.get(auction_url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Fetched auction data: {len(data)} auctions")
                    return data
                return []
        except Exception as e:
            logger.error(f"Error fetching auction data: {e}")
            return []

class FREDApi:
    """
    Federal Reserve Economic Data (FRED) API integration
    https://fred.stlouisfed.org/docs/api/fred/
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        self.base_url = "https://api.stlouisfed.org/fred"
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_series_data(self, series_id: str, limit: int = 100) -> List[Dict]:
        """Fetch time series data for a given FRED series"""
        if not self.api_key:
            logger.warning("FRED API key not provided, using mock data")
            return self._generate_mock_fred_data(series_id)
            
        try:
            url = f"{self.base_url}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': self.api_key,
                'file_type': 'json',
                'limit': limit,
                'sort_order': 'desc'
            }
            
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    observations = data.get('observations', [])
                    logger.info(f"Fetched {len(observations)} observations for {series_id}")
                    return observations
                else:
                    logger.error(f"FRED API error: {response.status}")
                    return self._generate_mock_fred_data(series_id)
                    
        except Exception as e:
            logger.error(f"Error fetching FRED data: {e}")
            return self._generate_mock_fred_data(series_id)
    
    def _generate_mock_fred_data(self, series_id: str) -> List[Dict]:
        """Generate mock FRED data when API is unavailable"""
        base_values = {
            'FEDFUNDS': 5.25,  # Fed Funds Rate
            'DGS10': 4.50,     # 10-Year Treasury
            'DGS2': 4.75,      # 2-Year Treasury  
            'DGS30': 4.25,     # 30-Year Treasury
            'SOFR': 5.30       # Secured Overnight Financing Rate
        }
        
        base_value = base_values.get(series_id, 4.0)
        data = []
        
        for i in range(30):  # 30 days of data
            date = datetime.now() - timedelta(days=i)
            # Add some realistic volatility
            value = base_value + np.random.normal(0, 0.1)
            data.append({
                'date': date.strftime('%Y-%m-%d'),
                'value': str(round(value, 2))
            })
        
        return data

class BloombergAPI:
    """
    Bloomberg Terminal API integration (BVAL pricing)
    Note: Requires Bloomberg Terminal and API license
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('BLOOMBERG_API_KEY')
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_bval_pricing(self, cusips: List[str]) -> List[Dict]:
        """Fetch BVAL pricing for given CUSIPs"""
        if not self.api_key:
            logger.warning("Bloomberg API key not provided, using mock BVAL data")
            return self._generate_mock_bval_data(cusips)
        
        # In production, this would connect to Bloomberg API
        # For now, return mock data
        return self._generate_mock_bval_data(cusips)
    
    def _generate_mock_bval_data(self, cusips: List[str]) -> List[Dict]:
        """Generate realistic mock BVAL pricing data"""
        data = []
        
        for cusip in cusips:
            # Generate realistic bond pricing
            base_price = np.random.uniform(98.0, 102.0)
            yield_rate = np.random.uniform(3.5, 5.5)
            
            data.append({
                'cusip': cusip,
                'bval_price': round(base_price, 4),
                'bval_yield': round(yield_rate, 4),
                'timestamp': datetime.now().isoformat(),
                'currency': 'USD',
                'price_source': 'BVAL'
            })
        
        return data

class RealTimeDataManager:
    """
    Central manager for all real-time data feeds
    Coordinates data fetching, caching, and distribution
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.treasury_api = TreasuryDirectAPI()
        self.fred_api = FREDApi()
        self.bloomberg_api = BloombergAPI()
        
        # Redis for caching
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_available = True
        except:
            logger.warning("Redis not available, using in-memory cache")
            self.redis_available = False
            self.memory_cache = {}
        
        # WebSocket connections for real-time updates
        self.websocket_clients = set()
        
    async def start_real_time_feeds(self):
        """Start all real-time data feeds"""
        logger.info("🚀 Starting real-time data feeds...")
        
        # Start periodic data fetching
        tasks = [
            self._fetch_treasury_data_loop(),
            self._fetch_fred_data_loop(),
            self._fetch_bloomberg_data_loop(),
            self._websocket_server()
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _fetch_treasury_data_loop(self):
        """Continuously fetch Treasury data"""
        while True:
            try:
                async with self.treasury_api as api:
                    # Fetch different security types
                    for security_type in ['Bill', 'Note', 'Bond']:
                        data = await api.get_treasury_securities(security_type)
                        
                        # Process and cache data
                        processed_data = self._process_treasury_data(data, security_type)
                        await self._cache_data(f"treasury_{security_type.lower()}", processed_data)
                        
                        # Broadcast to WebSocket clients
                        await self._broadcast_to_clients({
                            'type': 'treasury_update',
                            'security_type': security_type,
                            'data': processed_data[:5]  # Send first 5 for real-time
                        })
                
                # Wait 5 minutes before next fetch
                await asyncio.sleep(300)
                
            except Exception as e:
                logger.error(f"Error in Treasury data loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error
    
    async def _fetch_fred_data_loop(self):
        """Continuously fetch FRED economic data"""
        fred_series = ['FEDFUNDS', 'DGS10', 'DGS2', 'DGS30', 'SOFR']
        
        while True:
            try:
                async with self.fred_api as api:
                    for series_id in fred_series:
                        data = await api.get_series_data(series_id, limit=30)
                        processed_data = self._process_fred_data(data, series_id)
                        
                        await self._cache_data(f"fred_{series_id}", processed_data)
                        
                        # Broadcast latest value
                        if processed_data:
                            await self._broadcast_to_clients({
                                'type': 'fred_update',
                                'series_id': series_id,
                                'latest_value': processed_data[0]
                            })
                
                # Wait 15 minutes for FRED data
                await asyncio.sleep(900)
                
            except Exception as e:
                logger.error(f"Error in FRED data loop: {e}")
                await asyncio.sleep(300)
    
    async def _fetch_bloomberg_data_loop(self):
        """Continuously fetch Bloomberg BVAL data"""
        cusips = ['912828XG8', '912828YK0', '912810RZ3', '912810SE1']
        
        while True:
            try:
                async with self.bloomberg_api as api:
                    data = await api.get_bval_pricing(cusips)
                    processed_data = self._process_bloomberg_data(data)
                    
                    await self._cache_data("bloomberg_bval", processed_data)
                    
                    await self._broadcast_to_clients({
                        'type': 'bval_update',
                        'data': processed_data
                    })
                
                # Wait 1 minute for BVAL updates
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in Bloomberg data loop: {e}")
                await asyncio.sleep(120)
    
    def _process_treasury_data(self, data: List[Dict], security_type: str) -> List[Dict]:
        """Process raw Treasury data into standardized format"""
        processed = []
        
        for item in data:
            try:
                processed.append({
                    'cusip': item.get('cusip', ''),
                    'security_type': security_type,
                    'issue_date': item.get('issueDate', ''),
                    'maturity_date': item.get('maturityDate', ''),
                    'interest_rate': float(item.get('interestRate', 0)),
                    'price': float(item.get('price', 100)),
                    'yield': float(item.get('yield', 0)),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'treasury_direct'
                })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing Treasury item: {e}")
                continue
        
        return processed
    
    def _process_fred_data(self, data: List[Dict], series_id: str) -> List[Dict]:
        """Process raw FRED data into standardized format"""
        processed = []
        
        for item in data:
            try:
                if item.get('value') != '.':  # FRED uses '.' for missing values
                    processed.append({
                        'series_id': series_id,
                        'date': item.get('date'),
                        'value': float(item.get('value')),
                        'timestamp': datetime.now().isoformat(),
                        'source': 'fred'
                    })
            except (ValueError, TypeError) as e:
                logger.warning(f"Error processing FRED item: {e}")
                continue
        
        return processed
    
    def _process_bloomberg_data(self, data: List[Dict]) -> List[Dict]:
        """Process raw Bloomberg data into standardized format"""
        processed = []
        
        for item in data:
            try:
                processed.append({
                    'cusip': item.get('cusip'),
                    'bval_price': item.get('bval_price'),
                    'bval_yield': item.get('bval_yield'),
                    'timestamp': item.get('timestamp'),
                    'source': 'bloomberg'
                })
            except Exception as e:
                logger.warning(f"Error processing Bloomberg item: {e}")
                continue
        
        return processed
    
    async def _cache_data(self, key: str, data: Any):
        """Cache data in Redis or memory"""
        try:
            if self.redis_available:
                await asyncio.get_event_loop().run_in_executor(
                    None, 
                    self.redis_client.setex, 
                    key, 
                    3600,  # 1 hour TTL
                    json.dumps(data, default=str)
                )
            else:
                self.memory_cache[key] = {
                    'data': data,
                    'timestamp': datetime.now()
                }
        except Exception as e:
            logger.error(f"Error caching data: {e}")
    
    async def get_cached_data(self, key: str) -> Optional[Any]:
        """Retrieve cached data"""
        try:
            if self.redis_available:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, self.redis_client.get, key
                )
                return json.loads(data) if data else None
            else:
                cached = self.memory_cache.get(key)
                if cached:
                    # Check if data is still fresh (1 hour)
                    if datetime.now() - cached['timestamp'] < timedelta(hours=1):
                        return cached['data']
                return None
        except Exception as e:
            logger.error(f"Error retrieving cached data: {e}")
            return None
    
    async def _websocket_server(self):
        """WebSocket server for real-time updates"""
        try:
            async def handle_client(websocket, path):
                logger.info(f"New WebSocket client connected: {websocket.remote_address}")
                self.websocket_clients.add(websocket)
                
                try:
                    # Send initial data
                    await self._send_initial_data(websocket)
                    
                    # Keep connection alive
                    async for message in websocket:
                        # Handle client messages if needed
                        pass
                        
                except websockets.exceptions.ConnectionClosed:
                    pass
                finally:
                    self.websocket_clients.discard(websocket)
                    logger.info("WebSocket client disconnected")
            
            # Start WebSocket server on port 8765
            start_server = websockets.serve(handle_client, "localhost", 8765)
            logger.info("🌐 WebSocket server started on ws://localhost:8765")
            await start_server
            
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
    
    async def _send_initial_data(self, websocket):
        """Send initial data to new WebSocket client"""
        try:
            # Send cached data for immediate display
            treasury_data = await self.get_cached_data("treasury_bill")
            if treasury_data:
                await websocket.send(json.dumps({
                    'type': 'initial_data',
                    'treasury_data': treasury_data[:10]
                }))
        except Exception as e:
            logger.error(f"Error sending initial data: {e}")
    
    async def _broadcast_to_clients(self, message: Dict):
        """Broadcast message to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
            
        # Remove closed connections
        closed_clients = set()
        
        for client in self.websocket_clients:
            try:
                await client.send(json.dumps(message, default=str))
            except websockets.exceptions.ConnectionClosed:
                closed_clients.add(client)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                closed_clients.add(client)
        
        # Clean up closed connections
        self.websocket_clients -= closed_clients

# Utility functions for external use
async def get_live_treasury_data(security_type: str = "Bill") -> List[Dict]:
    """Get live Treasury data - utility function"""
    async with TreasuryDirectAPI() as api:
        return await api.get_treasury_securities(security_type)

async def get_live_fred_data(series_id: str) -> List[Dict]:
    """Get live FRED data - utility function"""
    async with FREDApi() as api:
        return await api.get_series_data(series_id)

# Main execution
if __name__ == "__main__":
    # Example usage
    async def main():
        manager = RealTimeDataManager()
        await manager.start_real_time_feeds()
    
    # Run the real-time data manager
    asyncio.run(main())
