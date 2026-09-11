from rest_framework import permissions

class IsStaffRole(permissions.BasePermission):
    """
    Pèmisyon pou nenpòt manm ekip sipèvizyon an (ADMIN, MODERATOR, OPERATOR, COMMUNICATOR).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in ['ADMIN', 'MODERATOR', 'OPERATOR', 'COMMUNICATOR'] or 
             request.user.is_staff or 
             request.user.is_superuser)
        )

class IsAdminRole(permissions.BasePermission):
    """
    Pèmisyon pou Administratè Siprèm (ADMIN oswa is_superuser).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role == 'ADMIN' or request.user.is_superuser)
        )

class CanModerateCandidates(permissions.BasePermission):
    """
    Pèmisyon pou analize ak apwouve/rejte/efase dosye kandida yo (ADMIN, MODERATOR).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in ['ADMIN', 'MODERATOR'] or request.user.is_superuser)
        )

class CanCreateCandidates(permissions.BasePermission):
    """
    Pèmisyon pou ajoute kandida dirèkteman nan panèl la (ADMIN, OPERATOR).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in ['ADMIN', 'OPERATOR'] or request.user.is_superuser)
        )

class CanManagePosts(permissions.BasePermission):
    """
    Pèmisyon pou kreye, modifye ak efase kominike / anons piblik (ADMIN, COMMUNICATOR).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in ['ADMIN', 'COMMUNICATOR'] or request.user.is_superuser)
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
