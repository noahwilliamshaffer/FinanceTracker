"""
Intelligent Alerting System
Advanced anomaly detection, threshold monitoring, and smart notifications
"""

import asyncio
import smtplib
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import requests
import os
from abc import ABC, abstractmethod

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    """Types of alerts"""
    SPREAD_ANOMALY = "spread_anomaly"
    PRICE_MOVEMENT = "price_movement"
    VOLUME_SPIKE = "volume_spike"
    YIELD_CURVE_INVERSION = "yield_curve_inversion"
    MARKET_STRESS = "market_stress"
    DATA_QUALITY = "data_quality"
    SYSTEM_ERROR = "system_error"
    CORRELATION_BREAK = "correlation_break"

@dataclass
class Alert:
    """Individual alert data structure"""
    id: str
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    timestamp: datetime
    source: str
    data: Dict[str, Any]
    resolved: bool = False
    acknowledged: bool = False
    resolution_timestamp: Optional[datetime] = None

@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    alert_type: AlertType
    severity: AlertSeverity
    condition: str  # Python expression to evaluate
    threshold: float
    lookback_period: int  # Minutes
    cooldown_period: int  # Minutes to wait before same alert
    enabled: bool = True
    description: str = ""

class NotificationChannel(ABC):
    """Abstract base class for notification channels"""
    
    @abstractmethod
    async def send_notification(self, alert: Alert) -> bool:
        """Send notification for an alert"""
        pass

class EmailNotifier(NotificationChannel):
    """Email notification channel"""
    
    def __init__(self, smtp_server: str, smtp_port: int, username: str, password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        
    async def send_notification(self, alert: Alert) -> bool:
        """Send email notification"""
        try:
            msg = MimeMultipart()
            msg['From'] = self.username
            msg['To'] = os.getenv('ALERT_EMAIL_RECIPIENTS', 'admin@company.com')
            msg['Subject'] = f"🚨 Finance Tracker Alert: {alert.title}"
            
            # Create HTML email body
            html_body = self._create_email_html(alert)
            msg.attach(MimeText(html_body, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            
            text = msg.as_string()
            server.sendmail(self.username, msg['To'], text)
            server.quit()
            
            logger.info(f"Email alert sent: {alert.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            return False
    
    def _create_email_html(self, alert: Alert) -> str:
        """Create HTML email template"""
        severity_colors = {
            AlertSeverity.LOW: "#28a745",
            AlertSeverity.MEDIUM: "#ffc107", 
            AlertSeverity.HIGH: "#fd7e14",
            AlertSeverity.CRITICAL: "#dc3545"
        }
        
        color = severity_colors.get(alert.severity, "#6c757d")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 20px;">
                <h2 style="color: {color}; margin-top: 0;">
                    {alert.severity.value.upper()} ALERT: {alert.title}
                </h2>
                
                <p><strong>Time:</strong> {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
                <p><strong>Type:</strong> {alert.alert_type.value.replace('_', ' ').title()}</p>
                <p><strong>Source:</strong> {alert.source}</p>
                
                <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 15px 0;">
                    <h3 style="margin-top: 0;">Message:</h3>
                    <p>{alert.message}</p>
                </div>
                
                {self._format_alert_data(alert.data)}
                
                <hr style="margin: 20px 0;">
                <p style="color: #6c757d; font-size: 12px;">
                    Finance Tracker Alert System - Alert ID: {alert.id}
                </p>
            </div>
        </body>
        </html>
        """
    
    def _format_alert_data(self, data: Dict[str, Any]) -> str:
        """Format alert data for email display"""
        if not data:
            return ""
            
        html = "<h3>Additional Data:</h3><ul>"
        for key, value in data.items():
            if isinstance(value, (int, float)):
                if key.endswith('_bps'):
                    html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value:.1f} bps</li>"
                elif key.endswith('_pct'):
                    html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value:.2%}</li>"
                else:
                    html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value:.4f}</li>"
            else:
                html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        html += "</ul>"
        
        return html

class SlackNotifier(NotificationChannel):
    """Slack notification channel"""
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        
    async def send_notification(self, alert: Alert) -> bool:
        """Send Slack notification"""
        try:
            severity_colors = {
                AlertSeverity.LOW: "#28a745",
                AlertSeverity.MEDIUM: "#ffc107",
                AlertSeverity.HIGH: "#fd7e14", 
                AlertSeverity.CRITICAL: "#dc3545"
            }
            
            severity_emojis = {
                AlertSeverity.LOW: "ℹ️",
                AlertSeverity.MEDIUM: "⚠️",
                AlertSeverity.HIGH: "🔥",
                AlertSeverity.CRITICAL: "🚨"
            }
            
            color = severity_colors.get(alert.severity, "#6c757d")
            emoji = severity_emojis.get(alert.severity, "📢")
            
            payload = {
                "attachments": [{
                    "color": color,
                    "title": f"{emoji} {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                        {"title": "Type", "value": alert.alert_type.value.replace('_', ' ').title(), "short": True},
                        {"title": "Source", "value": alert.source, "short": True},
                        {"title": "Time", "value": alert.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'), "short": True}
                    ],
                    "footer": f"Finance Tracker | Alert ID: {alert.id}"
                }]
            }
            
            response = requests.post(self.webhook_url, json=payload)
            
            if response.status_code == 200:
                logger.info(f"Slack alert sent: {alert.id}")
                return True
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

class AnomalyDetector:
    """Machine learning-based anomaly detection"""
    
    def __init__(self):
        self.isolation_forest = IsolationForest(contamination=0.1, random_state=42)
        self.scaler = StandardScaler()
        self.fitted = False
        
    def fit(self, data: pd.DataFrame) -> None:
        """Fit anomaly detection model"""
        try:
            # Prepare features for anomaly detection
            features = self._prepare_features(data)
            
            if len(features) > 10:  # Need minimum data for training
                scaled_features = self.scaler.fit_transform(features)
                self.isolation_forest.fit(scaled_features)
                self.fitted = True
                logger.info(f"Anomaly detector fitted with {len(features)} samples")
            else:
                logger.warning("Insufficient data for anomaly detection training")
                
        except Exception as e:
            logger.error(f"Error fitting anomaly detector: {e}")
    
    def detect_anomalies(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Detect anomalies in new data"""
        if not self.fitted:
            logger.warning("Anomaly detector not fitted, using simple threshold detection")
            return self._simple_anomaly_detection(data)
            
        try:
            features = self._prepare_features(data)
            scaled_features = self.scaler.transform(features)
            
            # Get anomaly scores (-1 for anomalies, 1 for normal)
            anomaly_scores = self.isolation_forest.predict(scaled_features)
            anomaly_probabilities = self.isolation_forest.score_samples(scaled_features)
            
            anomalies = []
            for i, (score, prob) in enumerate(zip(anomaly_scores, anomaly_probabilities)):
                if score == -1:  # Anomaly detected
                    anomalies.append({
                        'index': i,
                        'anomaly_score': prob,
                        'timestamp': data.index[i] if hasattr(data, 'index') else i,
                        'features': features.iloc[i].to_dict() if hasattr(features, 'iloc') else {}
                    })
            
            return anomalies
            
        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return []
    
    def _prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for anomaly detection"""
        features = pd.DataFrame()
        
        # Add numeric columns as features
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if col in ['spread_bps', 'volume_mm', 'price', 'yield']:
                features[col] = data[col]
                
                # Add rolling statistics as features
                if len(data) >= 5:
                    features[f'{col}_rolling_mean'] = data[col].rolling(5, min_periods=1).mean()
                    features[f'{col}_rolling_std'] = data[col].rolling(5, min_periods=1).std().fillna(0)
        
        return features.fillna(0)
    
    def _simple_anomaly_detection(self, data: pd.DataFrame) -> List[Dict[str, Any]]:
        """Simple threshold-based anomaly detection"""
        anomalies = []
        
        for col in ['spread_bps', 'volume_mm']:
            if col in data.columns:
                # Use 3-sigma rule
                mean_val = data[col].mean()
                std_val = data[col].std()
                threshold = 3 * std_val
                
                outliers = data[abs(data[col] - mean_val) > threshold]
                
                for idx, row in outliers.iterrows():
                    anomalies.append({
                        'index': idx,
                        'column': col,
                        'value': row[col],
                        'threshold': threshold,
                        'deviation': abs(row[col] - mean_val) / std_val
                    })
        
        return anomalies

class AlertEngine:
    """Main alert engine coordinating all alerting functionality"""
    
    def __init__(self):
        self.rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_channels: List[NotificationChannel] = []
        self.anomaly_detector = AnomalyDetector()
        self.last_alert_times: Dict[str, datetime] = {}
        
        # Load default alert rules
        self._load_default_rules()
        
    def add_notification_channel(self, channel: NotificationChannel):
        """Add a notification channel"""
        self.notification_channels.append(channel)
        
    def add_alert_rule(self, rule: AlertRule):
        """Add a new alert rule"""
        self.rules.append(rule)
        logger.info(f"Added alert rule: {rule.name}")
        
    def _load_default_rules(self):
        """Load default alert rules"""
        default_rules = [
            AlertRule(
                name="High Repo Spread",
                alert_type=AlertType.SPREAD_ANOMALY,
                severity=AlertSeverity.HIGH,
                condition="spread_bps > threshold",
                threshold=100.0,  # 100 basis points
                lookback_period=15,
                cooldown_period=60,
                description="Repo spread exceeds 100 basis points"
            ),
            AlertRule(
                name="Extreme Volume Spike",
                alert_type=AlertType.VOLUME_SPIKE,
                severity=AlertSeverity.MEDIUM,
                condition="volume_mm > threshold * avg_volume",
                threshold=3.0,  # 3x average volume
                lookback_period=30,
                cooldown_period=120,
                description="Trading volume exceeds 3x average"
            ),
            AlertRule(
                name="Yield Curve Inversion",
                alert_type=AlertType.YIELD_CURVE_INVERSION,
                severity=AlertSeverity.CRITICAL,
                condition="short_yield > long_yield",
                threshold=0.0,
                lookback_period=5,
                cooldown_period=360,  # 6 hours
                description="Yield curve inversion detected"
            ),
            AlertRule(
                name="Large Price Movement",
                alert_type=AlertType.PRICE_MOVEMENT,
                severity=AlertSeverity.MEDIUM,
                condition="abs(price_change_pct) > threshold",
                threshold=0.05,  # 5% price change
                lookback_period=60,
                cooldown_period=30,
                description="Bond price moved more than 5%"
            )
        ]
        
        self.rules.extend(default_rules)
        
    async def process_market_data(self, data: pd.DataFrame):
        """Process incoming market data and check for alerts"""
        try:
            # Check rule-based alerts
            await self._check_rule_based_alerts(data)
            
            # Check for anomalies
            await self._check_anomaly_alerts(data)
            
            # Update anomaly detector with new data
            if len(data) > 0:
                self.anomaly_detector.fit(data)
                
        except Exception as e:
            logger.error(f"Error processing market data for alerts: {e}")
    
    async def _check_rule_based_alerts(self, data: pd.DataFrame):
        """Check rule-based alerts"""
        for rule in self.rules:
            if not rule.enabled:
                continue
                
            try:
                # Check cooldown period
                rule_key = f"{rule.name}_{rule.alert_type.value}"
                last_alert_time = self.last_alert_times.get(rule_key)
                
                if last_alert_time:
                    time_since_last = (datetime.now() - last_alert_time).total_seconds() / 60
                    if time_since_last < rule.cooldown_period:
                        continue
                
                # Evaluate rule condition
                alert_triggered = await self._evaluate_rule_condition(rule, data)
                
                if alert_triggered:
                    alert = await self._create_alert_from_rule(rule, data)
                    await self._process_new_alert(alert)
                    self.last_alert_times[rule_key] = datetime.now()
                    
            except Exception as e:
                logger.error(f"Error checking rule {rule.name}: {e}")
    
    async def _evaluate_rule_condition(self, rule: AlertRule, data: pd.DataFrame) -> bool:
        """Evaluate if a rule condition is met"""
        try:
            # Get recent data based on lookback period
            if len(data) == 0:
                return False
                
            # Simple condition evaluation for demo
            if rule.alert_type == AlertType.SPREAD_ANOMALY:
                if 'spread_bps' in data.columns:
                    max_spread = data['spread_bps'].max()
                    return max_spread > rule.threshold
                    
            elif rule.alert_type == AlertType.VOLUME_SPIKE:
                if 'volume_mm' in data.columns:
                    current_volume = data['volume_mm'].iloc[-1] if len(data) > 0 else 0
                    avg_volume = data['volume_mm'].mean()
                    return current_volume > rule.threshold * avg_volume
                    
            elif rule.alert_type == AlertType.PRICE_MOVEMENT:
                if 'price' in data.columns and len(data) > 1:
                    price_change = (data['price'].iloc[-1] - data['price'].iloc[0]) / data['price'].iloc[0]
                    return abs(price_change) > rule.threshold
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating rule condition: {e}")
            return False
    
    async def _create_alert_from_rule(self, rule: AlertRule, data: pd.DataFrame) -> Alert:
        """Create an alert from a triggered rule"""
        alert_id = f"{rule.alert_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract relevant data for the alert
        alert_data = {}
        if 'spread_bps' in data.columns:
            alert_data['current_spread'] = float(data['spread_bps'].iloc[-1])
            alert_data['max_spread'] = float(data['spread_bps'].max())
        
        if 'volume_mm' in data.columns:
            alert_data['current_volume'] = float(data['volume_mm'].iloc[-1])
            alert_data['avg_volume'] = float(data['volume_mm'].mean())
        
        return Alert(
            id=alert_id,
            alert_type=rule.alert_type,
            severity=rule.severity,
            title=rule.name,
            message=f"{rule.description}. Threshold: {rule.threshold}",
            timestamp=datetime.now(),
            source="rule_engine",
            data=alert_data
        )
    
    async def _check_anomaly_alerts(self, data: pd.DataFrame):
        """Check for anomaly-based alerts"""
        try:
            anomalies = self.anomaly_detector.detect_anomalies(data)
            
            for anomaly in anomalies:
                alert = Alert(
                    id=f"anomaly_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{anomaly['index']}",
                    alert_type=AlertType.SPREAD_ANOMALY,
                    severity=AlertSeverity.MEDIUM,
                    title="Market Anomaly Detected",
                    message=f"Unusual market behavior detected with anomaly score: {anomaly.get('anomaly_score', 0):.3f}",
                    timestamp=datetime.now(),
                    source="anomaly_detector",
                    data=anomaly
                )
                
                await self._process_new_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking anomaly alerts: {e}")
    
    async def _process_new_alert(self, alert: Alert):
        """Process a new alert"""
        try:
            # Add to active alerts
            self.active_alerts[alert.id] = alert
            self.alert_history.append(alert)
            
            logger.info(f"New {alert.severity.value} alert: {alert.title}")
            
            # Send notifications
            await self._send_notifications(alert)
            
            # Log alert details
            self._log_alert(alert)
            
        except Exception as e:
            logger.error(f"Error processing new alert: {e}")
    
    async def _send_notifications(self, alert: Alert):
        """Send alert notifications to all channels"""
        for channel in self.notification_channels:
            try:
                success = await channel.send_notification(alert)
                if success:
                    logger.info(f"Alert {alert.id} sent via {type(channel).__name__}")
                else:
                    logger.warning(f"Failed to send alert {alert.id} via {type(channel).__name__}")
            except Exception as e:
                logger.error(f"Error sending notification via {type(channel).__name__}: {e}")
    
    def _log_alert(self, alert: Alert):
        """Log alert to file/database"""
        try:
            # In production, this would write to a database
            log_entry = {
                'timestamp': alert.timestamp.isoformat(),
                'alert_id': alert.id,
                'type': alert.alert_type.value,
                'severity': alert.severity.value,
                'title': alert.title,
                'message': alert.message,
                'source': alert.source,
                'data': alert.data
            }
            
            # Write to log file (in production, use proper logging infrastructure)
            with open('alerts.log', 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging alert: {e}")
    
    def acknowledge_alert(self, alert_id: str, user: str = "system") -> bool:
        """Acknowledge an alert"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].acknowledged = True
            logger.info(f"Alert {alert_id} acknowledged by {user}")
            return True
        return False
    
    def resolve_alert(self, alert_id: str, user: str = "system") -> bool:
        """Resolve an alert"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolution_timestamp = datetime.now()
            
            # Remove from active alerts
            del self.active_alerts[alert_id]
            
            logger.info(f"Alert {alert_id} resolved by {user}")
            return True
        return False
    
    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get active alerts, optionally filtered by severity"""
        alerts = list(self.active_alerts.values())
        
        if severity:
            alerts = [alert for alert in alerts if alert.severity == severity]
            
        return sorted(alerts, key=lambda x: x.timestamp, reverse=True)
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """Get alert statistics"""
        total_alerts = len(self.alert_history)
        active_count = len(self.active_alerts)
        
        # Count by severity
        severity_counts = {}
        for severity in AlertSeverity:
            count = sum(1 for alert in self.alert_history if alert.severity == severity)
            severity_counts[severity.value] = count
        
        # Count by type
        type_counts = {}
        for alert_type in AlertType:
            count = sum(1 for alert in self.alert_history if alert.alert_type == alert_type)
            type_counts[alert_type.value] = count
        
        return {
            'total_alerts': total_alerts,
            'active_alerts': active_count,
            'resolved_alerts': total_alerts - active_count,
            'severity_breakdown': severity_counts,
            'type_breakdown': type_counts,
            'last_24h': sum(1 for alert in self.alert_history 
                          if alert.timestamp > datetime.now() - timedelta(days=1))
        }

# Example usage and testing
if __name__ == "__main__":
    async def main():
        # Create alert engine
        engine = AlertEngine()
        
        # Add notification channels (mock for testing)
        # email_notifier = EmailNotifier("smtp.gmail.com", 587, "user@gmail.com", "password")
        # engine.add_notification_channel(email_notifier)
        
        # Generate sample data for testing
        sample_data = pd.DataFrame({
            'spread_bps': np.random.normal(25, 10, 100),
            'volume_mm': np.random.exponential(50, 100),
            'price': 100 + np.random.normal(0, 2, 100)
        })
        
        # Add some anomalies
        sample_data.loc[50, 'spread_bps'] = 150  # High spread
        sample_data.loc[75, 'volume_mm'] = 500   # High volume
        
        # Process the data
        await engine.process_market_data(sample_data)
        
        # Print results
        active_alerts = engine.get_active_alerts()
        print(f"Active alerts: {len(active_alerts)}")
        
        for alert in active_alerts:
            print(f"- {alert.severity.value.upper()}: {alert.title}")
        
        # Print statistics
        stats = engine.get_alert_statistics()
        print(f"\nAlert Statistics: {stats}")
    
    # Run the example
    asyncio.run(main())
