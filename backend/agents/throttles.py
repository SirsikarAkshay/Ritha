from rest_framework.throttling import UserRateThrottle


class AIAgentThrottle(UserRateThrottle):
    """50 AI agent calls per user per day."""
    scope = 'ai_agents'
