""
Consent Service - Ethics by Design

Purpose:
- Check if users have required consents before sensitive actions
- Enforce ethical data handling
- GDPR compliance
- Clear allow/deny decisions

This is a SERVICE layer - contains business logic, NO database code yet.

When DB is added:
- Replace in-memory storage with real queries
- Add methods: grant_consent(), revoke_consent()
- Add audit logging
- No changes to public API needed

Current Implementation:
- In-memory dictionary (temporary)
- Clear, testable logic
- Easy to add persistence later
"""

from typing import List, Dict, Optional
from datetime import datetime

from app.models.consent import (
    Consent,
    ConsentType,
    ConsentStatus,
    ConsentCheck,
    ConsentRequirement,
)


# ============================================================================
# CONSENT REQUIREMENTS MAPPING
# ============================================================================
# 
# This defines which actions require which consents.
# 
# Design Decision:
# - Centralized in one place (single source of truth)
# - Easy to update as platform evolves
# - Clear documentation for developers
# - Type-safe with ConsentRequirement model
#
# How to use:
#   required = CONSENT_REQUIREMENTS["save_trial"]
#   check = await consent_service.check_consent(user_id, required.required_consents)
#
# ============================================================================

CONSENT_REQUIREMENTS: Dict[str, ConsentRequirement] = {
    # Basic Platform Usage
    "register": ConsentRequirement(
        action="register",
        required_consents=[
            ConsentType.TERMS_OF_SERVICE,
            ConsentType.PRIVACY_POLICY,
        ],
        description="Users must accept Terms of Service and Privacy Policy to create an account",
        is_optional=False,
    ),
    
    # Trial-Related Actions
    "save_trial": ConsentRequirement(
        action="save_trial",
        required_consents=[
            ConsentType.DATA_SHARING,
        ],
        description="Users must consent to data sharing to save trials to their profile",
        is_optional=False,
    ),
    
    "connect_to_trial": ConsentRequirement(
        action="connect_to_trial",
        required_consents=[
            ConsentType.DATA_SHARING,
            ConsentType.RESEARCH_PARTICIPATION,
        ],
        description="Users must consent to data sharing and research participation to connect with trial organizers",
        is_optional=False,
    ),
    
    "submit_observation": ConsentRequirement(
        action="submit_observation",
        required_consents=[
            ConsentType.DATA_SHARING,
            ConsentType.RESEARCH_PARTICIPATION,
        ],
        description="Users must consent to sharing data for research purposes",
        is_optional=False,
    ),
    
    # Communication Actions
    "receive_trial_notifications": ConsentRequirement(
        action="receive_trial_notifications",
        required_consents=[
            ConsentType.CONTACT_TRIALS,
            ConsentType.EMAIL_NOTIFICATIONS,
        ],
        description="Users must consent to being contacted about new trials",
        is_optional=True,  # Users can opt out
    ),
    
    "receive_sms": ConsentRequirement(
        action="receive_sms",
        required_consents=[
            ConsentType.SMS_NOTIFICATIONS,
        ],
        description="Users must consent to receiving SMS notifications",
        is_optional=True,
    ),
}


class ConsentService:
    """
    Service for checking and managing user consents.
    
    Current Implementation:
    - In-memory storage (temporary)
    - Will be replaced with database queries
    
    Future Implementation (when DB is added):
    
        async def check_consent(self, user_id: int, required: List[ConsentType]):
            query = '''
                SELECT consent_type, status
                FROM consent_records
                WHERE user_id = $1
                  AND consent_type = ANY($2)
                  AND status = 'granted'
                  AND deleted_at IS NULL
                  AND (expires_at IS NULL OR expires_at > NOW())
            '''
            rows = await PostgresDB.fetch_all(query, user_id, required)
            # ... process rows ...
    
    """
    
    def __init__(self):
        """
        Initialize consent service.
        
        For now:
        - Uses in-memory dictionary
        
        When DB is added:
        - Remove this dictionary
        - Use PostgresDB.fetch_all() instead
        """
        # Temporary in-memory storage
        # Structure: {user_id: {consent_type: Consent}}
        self._consents: Dict[int, Dict[ConsentType, Consent]] = {}
    
    # ========================================================================
    # PUBLIC API - These methods will stay the same when DB is added
    # ========================================================================
    
    async def check_consent(
        self,
        user_id: int,
        required_consents: List[ConsentType],
    ) -> ConsentCheck:
        """
        Check if a user has all required consents.
        
        Args:
            user_id: ID of the user to check
            required_consents: List of consent types required
        
        Returns:
            ConsentCheck object with allow/deny decision
        
        Example:
            check = await consent_service.check_consent(
                user_id=123,
                required_consents=[ConsentType.DATA_SHARING]
            )
            
            if not check.is_allowed:
                raise ConsentRequiredError(
                    f"Missing consents: {check.missing_consents}"
                )
        
        When DB is added:
            Replace _get_user_consents() with SQL query
        """
        # Get all consents for this user
        user_consents = await self._get_user_consents(user_id)
        
        # Filter to active (granted, not expired) consents
        granted = [
            consent_type
            for consent_type, consent in user_consents.items()
            if consent.is_active
        ]
        
        # Find missing consents
        missing = [
            consent_type
            for consent_type in required_consents
            if consent_type not in granted
        ]
        
        # Build result
        return ConsentCheck(
            user_id=user_id,
            required_consents=required_consents,
            granted_consents=granted,
            missing_consents=missing,
            is_allowed=len(missing) == 0,
        )
    
    async def check_action(
        self,
        user_id: int,
        action: str,
    ) -> ConsentCheck:
        """
        Check if a user can perform a specific action.
        
        This is a convenience method that looks up required consents
        from CONSENT_REQUIREMENTS.
        
        Args:
            user_id: ID of the user
            action: Action name (e.g., "save_trial")
        
        Returns:
            ConsentCheck object
        
        Raises:
            ValueError: If action is not defined in CONSENT_REQUIREMENTS
        
        Example:
            check = await consent_service.check_action(
                user_id=123,
                action="save_trial"
            )
            
            if not check.is_allowed:
                return {
                    "error": "consent_required",
                    "missing": check.missing_consents
                }
        """
        if action not in CONSENT_REQUIREMENTS:
            raise ValueError(
                f"Unknown action '{action}'. "
                f"Available: {list(CONSENT_REQUIREMENTS.keys())}"
            )
        
        requirement = CONSENT_REQUIREMENTS[action]
        return await self.check_consent(user_id, requirement.required_consents)
    
    async def get_consent_status(
        self,
        user_id: int,
        consent_type: ConsentType,
    ) -> Optional[Consent]:
        """
        Get the current status of a specific consent.
        
        Args:
            user_id: ID of the user
            consent_type: Type of consent to check
        
        Returns:
            Consent object if exists, None otherwise
        
        When DB is added:
            SELECT * FROM consent_records
            WHERE user_id = $1
              AND consent_type = $2
              AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
        """
        user_consents = await self._get_user_consents(user_id)
        return user_consents.get(consent_type)
    
    # ========================================================================
    # ADMIN METHODS - For testing and development
    # ========================================================================
    # These will be removed when DB is added
    # ========================================================================
    
    async def _grant_consent_temporary(
        self,
        user_id: int,
        consent_type: ConsentType,
        version: str = "1.0",
    ) -> Consent:
        """
        TEMPORARY: Grant consent for testing.
        
        This method will be REMOVED when database is added.
        
        When DB is added:
            INSERT INTO consent_records (
                user_id, consent_type, status, version, granted_at
            ) VALUES ($1, $2, 'granted', $3, NOW())
            RETURNING *
        """
        consent = Consent(
            user_id=user_id,
            consent_type=consent_type,
            status=ConsentStatus.GRANTED,
            version=version,
            granted_at=datetime.utcnow(),
        )
        
        if user_id not in self._consents:
            self._consents[user_id] = {}
        
        self._consents[user_id][consent_type] = consent
        return consent
    
    async def _revoke_consent_temporary(
        self,
        user_id: int,
        consent_type: ConsentType,
    ) -> Optional[Consent]:
        """
        TEMPORARY: Revoke consent for testing.
        
        This method will be REMOVED when database is added.
        
        When DB is added:
            UPDATE consent_records
            SET status = 'revoked',
                revoked_at = NOW(),
                updated_at = NOW()
            WHERE user_id = $1
              AND consent_type = $2
              AND status = 'granted'
            RETURNING *
        """
        user_consents = await self._get_user_consents(user_id)
        
        if consent_type not in user_consents:
            return None
        
        consent = user_consents[consent_type]
        consent.status = ConsentStatus.REVOKED
        consent.revoked_at = datetime.utcnow()
        
        return consent
    
    # ========================================================================
    # PRIVATE HELPERS - Will be replaced with SQL
    # ========================================================================
    
    async def _get_user_consents(
        self,
        user_id: int,
    ) -> Dict[ConsentType, Consent]:
        """
        Get all consents for a user.
        
        When DB is added:
            SELECT *
            FROM consent_records
            WHERE user_id = $1
              AND deleted_at IS NULL
            ORDER BY created_at DESC
        """
        return self._consents.get(user_id, {})


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================
# Create a single instance to use across the application
# ============================================================================

consent_service = ConsentService()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def require_consent(action: str):
    """
    Decorator to require consent for API endpoints.
    
    Example:
        @app.post("/trials/{trial_id}/save")
        @require_consent("save_trial")
        async def save_trial(trial_id: int, user_id: int):
            # Will only execute if user has required consents
            pass
    
    This is a FUTURE feature - not implemented yet.
    Will be added when we have proper dependency injection.
    """
    # TODO: Implement when we add dependency injection
    raise NotImplementedError("Decorator not implemented yet")


def get_action_requirements(action: str) -> Optional[ConsentRequirement]:
    """
    Get consent requirements for an action.
    
    Args:
        action: Action name
    
    Returns:
        ConsentRequirement if action exists, None otherwise
    
    Example:
        req = get_action_requirements("save_trial")
        print(req.description)
        # "Users must consent to data sharing to save trials to their profile"
    """
    return CONSENT_REQUIREMENTS.get(action)


def list_all_actions() -> List[str]:
    """
    List all actions that require consent.
    
    Returns:
        List of action names
    
    Example:
        actions = list_all_actions()
        # ["register", "save_trial", "connect_to_trial", ...]
    """
    return list(CONSENT_REQUIREMENTS.keys())
