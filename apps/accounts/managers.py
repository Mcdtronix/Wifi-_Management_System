"""
apps/accounts/managers.py
--------------------------
Custom manager for the AdminUser model.

Django requires a custom manager whenever you subclass AbstractBaseUser so it
knows how to create users and superusers correctly (the built-in UserManager
assumes a `username` field which AdminUser does not have).
"""

from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _


class AdminUserManager(BaseUserManager):
    """
    Manager for AdminUser where email is the unique identifier
    instead of the default username.
    """

    def create_user(self, email: str, password: str, **extra_fields):
        """
        Create and save an AdminUser with the given email and password.

        This is the standard path for programmatic user creation (e.g. tests,
        management commands, and the admin panel).
        """
        if not email:
            raise ValueError(_("An email address is required."))

        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        # Call save() directly rather than full_clean() here — the model's
        # own save() calls full_clean(), so validation still runs.
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        """
        Create and save a superuser (has all permissions + Django admin access).

        Called by:  python manage.py createsuperuser
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)
