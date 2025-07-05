from rest_framework import permissions


class IsSuperAdmin(permissions.BasePermission):
    """
    Доступ только для супер-админа
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "superadmin"


class IsBathAdminOrSuperAdmin(permissions.BasePermission):
    """
    Доступ для bath_admin к своим объектам, или для супер-админа ко всем
    """

    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.role == "bath_admin" or request.user.role == "superadmin"
        )
