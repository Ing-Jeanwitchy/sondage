from rest_framework import permissions

class IsAdminRole(permissions.BasePermission):
    """
    Pèmisyon pou Administratè sèlman (ADMIN oswa is_staff).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'ADMIN' or request.user.is_staff or request.user.is_superuser)
        )

class IsCandidateRole(permissions.BasePermission):
    """
    Pèmisyon pou Kandida sèlman (CANDIDATE).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'CANDIDATE'
        )

class IsVoterRole(permissions.BasePermission):
    """
    Pèmisyon pou Patisipan / Elektè sèlman (VOTER).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.role == 'VOTER'
        )
