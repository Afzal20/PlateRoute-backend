from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from .otp import generate_otp, hash_otp


class PasswordResetOTP(models.Model):
    """A hashed, single-use, short-lived code for password resets.

    The raw code is emailed to the user; only its SHA-256 hash is stored.
    """

    TTL_MINUTES = 15

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="password_otps")
    code_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["code_hash"])]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self._state.adding and self.expires_at is None:
            self.expires_at = timezone.now() + timedelta(minutes=self.TTL_MINUTES)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    def is_valid(self):
        return not self.used and not self.is_expired

    @classmethod
    def issue(cls, user):
        """Create a fresh code for ``user``, discarding outstanding ones.

        Returns ``(instance, raw_code)`` — the raw code exists only long
        enough to be emailed and is never written to the database.
        """
        cls.objects.filter(user=user, used=False).delete()
        raw_code = generate_otp()
        instance = cls.objects.create(user=user, code_hash=hash_otp(raw_code))
        return instance, raw_code


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts_user"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    token_version = models.PositiveIntegerField(default=0)

    def bump_token_version(self):
        self.token_version += 1
        self.save(update_fields=["token_version"])
