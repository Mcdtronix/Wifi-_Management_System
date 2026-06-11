from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils.translation import gettext_lazy as _

class MultiUserJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication backend that supports both AdminUser and Subscriber.
    It reads a custom 'user_type' claim from the JWT token.
    """

    def get_user(self, validated_token):
        """
        Attempts to find and return a user using the given validated token.
        """
        user_type = validated_token.get('user_type', 'admin')
        user_id = validated_token.get('user_id')

        if not user_id:
            raise AuthenticationFailed(_('Token contained no recognizable user identification'), code='token_not_valid')

        if user_type == 'subscriber':
            from apps.subscribers.models import Subscriber
            try:
                user = Subscriber.objects.get(id=user_id)
            except Subscriber.DoesNotExist:
                raise AuthenticationFailed(_('Subscriber not found'), code='user_not_found')

            if user.account_status == Subscriber.AccountStatus.BANNED:
                raise AuthenticationFailed(_('Subscriber account is banned'), code='user_inactive')

            # Django REST framework permissions typically check `user.is_active`
            # For subscribers, we dynamically map `is_active` to whether they are accessible
            user.is_active = user.is_accessible
            
        else:
            from apps.accounts.models import AdminUser
            try:
                user = AdminUser.objects.get(id=user_id)
            except AdminUser.DoesNotExist:
                raise AuthenticationFailed(_('Admin not found'), code='user_not_found')

            if not user.is_active:
                raise AuthenticationFailed(_('User is inactive'), code='user_inactive')

        return user
