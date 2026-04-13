from rest_framework.permissions import BasePermission

class IsProductOwner(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Product Owner').exists()

class IsDeveloper(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Developer').exists()

class IsBetaTester(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.groups.filter(name='Beta Tester').exists()

class IsProductOwnerOrDeveloper(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and (
                request.user.groups.filter(name='Product Owner').exists()
                or request.user.groups.filter(name='Developer').exists()
            )
        )