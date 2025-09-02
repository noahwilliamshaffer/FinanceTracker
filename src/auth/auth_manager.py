"""
User Authentication and Role-Based Access Control System
Comprehensive user management with JWT tokens, role-based permissions, and audit logging
"""

import jwt
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import uuid
from functools import wraps
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import redis
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserRole(Enum):
    """User roles with hierarchical permissions"""
    ADMIN = "admin"
    RISK_MANAGER = "risk_manager"
    PORTFOLIO_MANAGER = "portfolio_manager"
    TRADER = "trader"
    ANALYST = "analyst"
    VIEWER = "viewer"

class Permission(Enum):
    """System permissions"""
    # Data permissions
    VIEW_MARKET_DATA = "view_market_data"
    EDIT_MARKET_DATA = "edit_market_data"
    EXPORT_DATA = "export_data"
    
    # Portfolio permissions
    VIEW_PORTFOLIO = "view_portfolio"
    EDIT_PORTFOLIO = "edit_portfolio"
    EXECUTE_TRADES = "execute_trades"
    
    # Risk permissions
    VIEW_RISK_METRICS = "view_risk_metrics"
    EDIT_RISK_LIMITS = "edit_risk_limits"
    APPROVE_TRADES = "approve_trades"
    
    # Analytics permissions
    VIEW_ANALYTICS = "view_analytics"
    CREATE_REPORTS = "create_reports"
    
    # System permissions
    MANAGE_USERS = "manage_users"
    MANAGE_SYSTEM = "manage_system"
    VIEW_AUDIT_LOGS = "view_audit_logs"
    
    # Alert permissions
    VIEW_ALERTS = "view_alerts"
    MANAGE_ALERTS = "manage_alerts"

@dataclass
class User:
    """User account information"""
    user_id: str
    username: str
    email: str
    full_name: str
    role: UserRole
    permissions: Set[Permission] = field(default_factory=set)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    last_login: Optional[datetime] = None
    failed_login_attempts: int = 0
    password_hash: Optional[str] = None
    api_key: Optional[str] = None
    session_timeout_minutes: int = 480  # 8 hours
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Session:
    """User session information"""
    session_id: str
    user_id: str
    username: str
    role: UserRole
    permissions: Set[Permission]
    created_at: datetime
    expires_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_active: bool = True

@dataclass
class AuditLogEntry:
    """Audit log entry for security tracking"""
    log_id: str
    user_id: str
    username: str
    action: str
    resource: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    success: bool = True

class RolePermissionManager:
    """Manages role-based permissions"""
    
    # Define role-permission mappings
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            Permission.VIEW_MARKET_DATA, Permission.EDIT_MARKET_DATA, Permission.EXPORT_DATA,
            Permission.VIEW_PORTFOLIO, Permission.EDIT_PORTFOLIO, Permission.EXECUTE_TRADES,
            Permission.VIEW_RISK_METRICS, Permission.EDIT_RISK_LIMITS, Permission.APPROVE_TRADES,
            Permission.VIEW_ANALYTICS, Permission.CREATE_REPORTS,
            Permission.MANAGE_USERS, Permission.MANAGE_SYSTEM, Permission.VIEW_AUDIT_LOGS,
            Permission.VIEW_ALERTS, Permission.MANAGE_ALERTS
        },
        UserRole.RISK_MANAGER: {
            Permission.VIEW_MARKET_DATA, Permission.EXPORT_DATA,
            Permission.VIEW_PORTFOLIO, Permission.VIEW_RISK_METRICS, 
            Permission.EDIT_RISK_LIMITS, Permission.APPROVE_TRADES,
            Permission.VIEW_ANALYTICS, Permission.CREATE_REPORTS,
            Permission.VIEW_ALERTS, Permission.MANAGE_ALERTS
        },
        UserRole.PORTFOLIO_MANAGER: {
            Permission.VIEW_MARKET_DATA, Permission.EXPORT_DATA,
            Permission.VIEW_PORTFOLIO, Permission.EDIT_PORTFOLIO, Permission.EXECUTE_TRADES,
            Permission.VIEW_RISK_METRICS, Permission.VIEW_ANALYTICS, Permission.CREATE_REPORTS,
            Permission.VIEW_ALERTS
        },
        UserRole.TRADER: {
            Permission.VIEW_MARKET_DATA, Permission.VIEW_PORTFOLIO, 
            Permission.EXECUTE_TRADES, Permission.VIEW_RISK_METRICS,
            Permission.VIEW_ANALYTICS, Permission.VIEW_ALERTS
        },
        UserRole.ANALYST: {
            Permission.VIEW_MARKET_DATA, Permission.EXPORT_DATA,
            Permission.VIEW_PORTFOLIO, Permission.VIEW_RISK_METRICS,
            Permission.VIEW_ANALYTICS, Permission.CREATE_REPORTS,
            Permission.VIEW_ALERTS
        },
        UserRole.VIEWER: {
            Permission.VIEW_MARKET_DATA, Permission.VIEW_PORTFOLIO,
            Permission.VIEW_RISK_METRICS, Permission.VIEW_ANALYTICS
        }
    }
    
    @classmethod
    def get_permissions_for_role(cls, role: UserRole) -> Set[Permission]:
        """Get all permissions for a role"""
        return cls.ROLE_PERMISSIONS.get(role, set())
    
    @classmethod
    def has_permission(cls, user_role: UserRole, permission: Permission) -> bool:
        """Check if a role has a specific permission"""
        return permission in cls.get_permissions_for_role(user_role)

class PasswordManager:
    """Secure password management"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_password_strength(password: str) -> Dict[str, Any]:
        """Validate password strength"""
        issues = []
        score = 0
        
        if len(password) >= 8:
            score += 1
        else:
            issues.append("Password must be at least 8 characters")
        
        if any(c.isupper() for c in password):
            score += 1
        else:
            issues.append("Password must contain uppercase letters")
        
        if any(c.islower() for c in password):
            score += 1
        else:
            issues.append("Password must contain lowercase letters")
        
        if any(c.isdigit() for c in password):
            score += 1
        else:
            issues.append("Password must contain numbers")
        
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        else:
            issues.append("Password must contain special characters")
        
        strength_levels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
        strength = strength_levels[min(score, 4)]
        
        return {
            'score': score,
            'strength': strength,
            'is_valid': score >= 3,
            'issues': issues
        }

class TokenManager:
    """JWT token management"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
        self.algorithm = 'HS256'
        self.access_token_expire_minutes = 480  # 8 hours
        self.refresh_token_expire_days = 30
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'role': user.role.value,
            'permissions': [p.value for p in user.permissions],
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire_days)
        
        payload = {
            'user_id': user.user_id,
            'username': user.username,
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token"""
        payload = self.verify_token(refresh_token)
        
        if payload.get('type') != 'refresh':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # In production, would fetch user from database
        # For now, create minimal user object
        user = User(
            user_id=payload['user_id'],
            username=payload['username'],
            email="",
            full_name="",
            role=UserRole.VIEWER  # Default role
        )
        
        return self.create_access_token(user)

class SessionManager:
    """User session management with Redis backend"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        try:
            self.redis_client = redis.from_url(redis_url)
            self.redis_available = True
        except:
            logger.warning("Redis not available, using in-memory session storage")
            self.redis_available = False
            self.memory_sessions: Dict[str, Session] = {}
    
    def create_session(self, user: User, ip_address: str = None, 
                      user_agent: str = None) -> Session:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        expire_time = datetime.now() + timedelta(minutes=user.session_timeout_minutes)
        
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            username=user.username,
            role=user.role,
            permissions=user.permissions,
            created_at=datetime.now(),
            expires_at=expire_time,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Store session
        if self.redis_available:
            try:
                session_data = {
                    'user_id': session.user_id,
                    'username': session.username,
                    'role': session.role.value,
                    'permissions': [p.value for p in session.permissions],
                    'created_at': session.created_at.isoformat(),
                    'expires_at': session.expires_at.isoformat(),
                    'ip_address': session.ip_address,
                    'user_agent': session.user_agent,
                    'is_active': session.is_active
                }
                
                self.redis_client.setex(
                    f"session:{session_id}",
                    user.session_timeout_minutes * 60,  # TTL in seconds
                    json.dumps(session_data, default=str)
                )
            except Exception as e:
                logger.error(f"Error storing session in Redis: {e}")
                self.memory_sessions[session_id] = session
        else:
            self.memory_sessions[session_id] = session
        
        logger.info(f"Created session {session_id} for user {user.username}")
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session"""
        try:
            if self.redis_available:
                session_data = self.redis_client.get(f"session:{session_id}")
                if session_data:
                    data = json.loads(session_data)
                    return Session(
                        session_id=session_id,
                        user_id=data['user_id'],
                        username=data['username'],
                        role=UserRole(data['role']),
                        permissions={Permission(p) for p in data['permissions']},
                        created_at=datetime.fromisoformat(data['created_at']),
                        expires_at=datetime.fromisoformat(data['expires_at']),
                        ip_address=data.get('ip_address'),
                        user_agent=data.get('user_agent'),
                        is_active=data.get('is_active', True)
                    )
            else:
                return self.memory_sessions.get(session_id)
        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
        
        return None
    
    def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        try:
            if self.redis_available:
                result = self.redis_client.delete(f"session:{session_id}")
                return result > 0
            else:
                return self.memory_sessions.pop(session_id, None) is not None
        except Exception as e:
            logger.error(f"Error invalidating session: {e}")
            return False
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions (for memory storage)"""
        if not self.redis_available:
            current_time = datetime.now()
            expired_sessions = [
                sid for sid, session in self.memory_sessions.items()
                if session.expires_at < current_time
            ]
            
            for sid in expired_sessions:
                del self.memory_sessions[sid]
            
            if expired_sessions:
                logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")

class AuditLogger:
    """Security audit logging"""
    
    def __init__(self):
        self.audit_logs: List[AuditLogEntry] = []
    
    def log_action(self, user_id: str, username: str, action: str, 
                  resource: str, success: bool = True,
                  ip_address: str = None, user_agent: str = None,
                  details: Dict[str, Any] = None):
        """Log a user action"""
        log_entry = AuditLogEntry(
            log_id=str(uuid.uuid4()),
            user_id=user_id,
            username=username,
            action=action,
            resource=resource,
            timestamp=datetime.now(),
            ip_address=ip_address,
            user_agent=user_agent,
            details=details or {},
            success=success
        )
        
        self.audit_logs.append(log_entry)
        
        # In production, would store in database
        logger.info(f"AUDIT: {username} {action} {resource} - {'SUCCESS' if success else 'FAILED'}")
        
        # Keep only last 10000 entries in memory
        if len(self.audit_logs) > 10000:
            self.audit_logs = self.audit_logs[-10000:]
    
    def get_audit_logs(self, user_id: str = None, action: str = None, 
                      hours: int = 24) -> List[AuditLogEntry]:
        """Get audit logs with optional filtering"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        filtered_logs = [
            log for log in self.audit_logs
            if log.timestamp > cutoff_time
        ]
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log.user_id == user_id]
        
        if action:
            filtered_logs = [log for log in filtered_logs if action.lower() in log.action.lower()]
        
        return sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

class AuthManager:
    """Main authentication and authorization manager"""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.token_manager = TokenManager()
        self.session_manager = SessionManager()
        self.audit_logger = AuditLogger()
        self.security = HTTPBearer()
        
        # Create default admin user
        self._create_default_users()
    
    def _create_default_users(self):
        """Create default system users"""
        # Admin user
        admin_user = User(
            user_id="admin-001",
            username="admin",
            email="admin@financetracker.com",
            full_name="System Administrator",
            role=UserRole.ADMIN,
            permissions=RolePermissionManager.get_permissions_for_role(UserRole.ADMIN),
            password_hash=PasswordManager.hash_password("admin123!"),  # Change in production
            api_key=PasswordManager.generate_api_key()
        )
        
        # Demo trader
        trader_user = User(
            user_id="trader-001",
            username="trader",
            email="trader@financetracker.com",
            full_name="Demo Trader",
            role=UserRole.TRADER,
            permissions=RolePermissionManager.get_permissions_for_role(UserRole.TRADER),
            password_hash=PasswordManager.hash_password("trader123!"),
            api_key=PasswordManager.generate_api_key()
        )
        
        # Demo analyst
        analyst_user = User(
            user_id="analyst-001",
            username="analyst",
            email="analyst@financetracker.com",
            full_name="Demo Analyst",
            role=UserRole.ANALYST,
            permissions=RolePermissionManager.get_permissions_for_role(UserRole.ANALYST),
            password_hash=PasswordManager.hash_password("analyst123!"),
            api_key=PasswordManager.generate_api_key()
        )
        
        self.users.update({
            admin_user.username: admin_user,
            trader_user.username: trader_user,
            analyst_user.username: analyst_user
        })
        
        logger.info("Created default users: admin, trader, analyst")
    
    def authenticate_user(self, username: str, password: str, 
                         ip_address: str = None, user_agent: str = None) -> Optional[Dict[str, Any]]:
        """Authenticate user with username/password"""
        user = self.users.get(username)
        
        if not user:
            self.audit_logger.log_action("", username, "LOGIN_ATTEMPT", "authentication", 
                                       False, ip_address, user_agent, 
                                       {"reason": "user_not_found"})
            return None
        
        if not user.is_active:
            self.audit_logger.log_action(user.user_id, username, "LOGIN_ATTEMPT", "authentication", 
                                       False, ip_address, user_agent,
                                       {"reason": "account_disabled"})
            return None
        
        # Check for account lockout (simple implementation)
        if user.failed_login_attempts >= 5:
            self.audit_logger.log_action(user.user_id, username, "LOGIN_ATTEMPT", "authentication", 
                                       False, ip_address, user_agent,
                                       {"reason": "account_locked"})
            return None
        
        if not PasswordManager.verify_password(password, user.password_hash):
            user.failed_login_attempts += 1
            self.audit_logger.log_action(user.user_id, username, "LOGIN_ATTEMPT", "authentication", 
                                       False, ip_address, user_agent,
                                       {"reason": "invalid_password", 
                                        "attempts": user.failed_login_attempts})
            return None
        
        # Successful login
        user.failed_login_attempts = 0
        user.last_login = datetime.now()
        
        # Create session and tokens
        session = self.session_manager.create_session(user, ip_address, user_agent)
        access_token = self.token_manager.create_access_token(user)
        refresh_token = self.token_manager.create_refresh_token(user)
        
        self.audit_logger.log_action(user.user_id, username, "LOGIN_SUCCESS", "authentication", 
                                   True, ip_address, user_agent)
        
        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_type': 'bearer',
            'expires_in': self.token_manager.access_token_expire_minutes * 60,
            'user': {
                'user_id': user.user_id,
                'username': user.username,
                'full_name': user.full_name,
                'role': user.role.value,
                'permissions': [p.value for p in user.permissions]
            },
            'session_id': session.session_id
        }
    
    def get_current_user(self, credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())) -> User:
        """Get current user from JWT token (for FastAPI dependency)"""
        try:
            payload = self.token_manager.verify_token(credentials.credentials)
            username = payload.get('username')
            
            if not username:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token payload"
                )
            
            user = self.users.get(username)
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )
            
            return user
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting current user: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed"
            )
    
    def require_permission(self, permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # In FastAPI, current_user would be injected as dependency
                current_user = kwargs.get('current_user')
                
                if not current_user:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
                
                if permission not in current_user.permissions:
                    self.audit_logger.log_action(
                        current_user.user_id, current_user.username,
                        "PERMISSION_DENIED", permission.value, False
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission required: {permission.value}"
                    )
                
                return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def logout_user(self, session_id: str, user_id: str, username: str):
        """Logout user and invalidate session"""
        success = self.session_manager.invalidate_session(session_id)
        
        self.audit_logger.log_action(user_id, username, "LOGOUT", "authentication", success)
        
        return success
    
    def create_user(self, username: str, email: str, full_name: str, 
                   role: UserRole, password: str, creator_user_id: str) -> User:
        """Create a new user (admin only)"""
        if username in self.users:
            raise ValueError(f"Username '{username}' already exists")
        
        # Validate password
        password_validation = PasswordManager.validate_password_strength(password)
        if not password_validation['is_valid']:
            raise ValueError(f"Password validation failed: {password_validation['issues']}")
        
        user = User(
            user_id=str(uuid.uuid4()),
            username=username,
            email=email,
            full_name=full_name,
            role=role,
            permissions=RolePermissionManager.get_permissions_for_role(role),
            password_hash=PasswordManager.hash_password(password),
            api_key=PasswordManager.generate_api_key()
        )
        
        self.users[username] = user
        
        self.audit_logger.log_action(creator_user_id, "", "CREATE_USER", f"user:{username}", True,
                                   details={"new_user_role": role.value})
        
        logger.info(f"Created user: {username} with role {role.value}")
        return user
    
    def get_user_info(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user information (excluding sensitive data)"""
        user = self.users.get(username)
        if not user:
            return None
        
        return {
            'user_id': user.user_id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role.value,
            'permissions': [p.value for p in user.permissions],
            'is_active': user.is_active,
            'created_at': user.created_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        }
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users (admin only)"""
        return [self.get_user_info(username) for username in self.users.keys()]

# Example usage and testing
if __name__ == "__main__":
    # Create auth manager
    auth = AuthManager()
    
    # Test authentication
    print("Testing authentication...")
    
    # Valid login
    result = auth.authenticate_user("admin", "admin123!", "127.0.0.1", "Test Client")
    if result:
        print(f"✅ Admin login successful")
        print(f"   Access token: {result['access_token'][:50]}...")
        print(f"   Role: {result['user']['role']}")
        print(f"   Permissions: {len(result['user']['permissions'])} permissions")
    
    # Invalid login
    result = auth.authenticate_user("admin", "wrongpassword", "127.0.0.1", "Test Client")
    if not result:
        print("✅ Invalid password correctly rejected")
    
    # Test user creation
    try:
        new_user = auth.create_user(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            role=UserRole.VIEWER,
            password="TestPass123!",
            creator_user_id="admin-001"
        )
        print(f"✅ Created user: {new_user.username}")
    except Exception as e:
        print(f"❌ User creation failed: {e}")
    
    # Get audit logs
    audit_logs = auth.audit_logger.get_audit_logs(hours=1)
    print(f"📊 Audit logs: {len(audit_logs)} entries in last hour")
    
    for log in audit_logs[:3]:  # Show first 3
        print(f"   {log.timestamp.strftime('%H:%M:%S')} - {log.username} {log.action} - {'✅' if log.success else '❌'}")
    
    print("\n🔐 Authentication system ready!")
