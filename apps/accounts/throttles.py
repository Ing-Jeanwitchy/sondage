from rest_framework.throttling import AnonRateThrottle, UserRateThrottle

class AuthRateThrottle(AnonRateThrottle):
    """
    Limitasyon debil pou tantativ koneksyon ak enskripsyon (Anti-Brute Force).
    """
    scope = 'auth'


class VoteRateThrottle(UserRateThrottle):
    """
    Limitasyon debil pou anrejistreman vòt (Anti-Spam / Anti-Bot).
    """
    scope = 'votes'
