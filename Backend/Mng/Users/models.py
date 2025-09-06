from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin, Group, Permission

from django.db import models
from django.utils import timezone
from datetime import timedelta

class OTP(models.Model):
    phone_number = models.CharField(max_length=15)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=5)  # 5 mins validity

# Custom user manager
class UserManager(BaseUserManager):
    def create_user(self, phone_number, username, email=None, password=None):
        if not phone_number:
            raise ValueError("Users must have a phone number")
        if not username:
            raise ValueError("Users must have a username")

        user = self.model(phone_number=phone_number, username=username, email=email)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, username, email=None, password=None):
        user = self.create_user(
            phone_number=phone_number,
            username=username,
            email=email,
            password=password
        )
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


# Custom User model
class Users(AbstractBaseUser, PermissionsMixin):
    phone_number = models.CharField(max_length=15, unique=True)  # ✅ Primary unique field
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)  # ✅ Not unique, optional

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(auto_now=True)

    groups = models.ManyToManyField(
        Group,
        related_name='custom_user_set',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='custom_user_permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    objects = UserManager()

    # ✅ Phone number is used for login instead of email
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username']  # email is optional

    def __str__(self):
        return self.phone_number


# Interest model
class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. "Football", "Tech", "Hiking"

    def __str__(self):
        return self.name


# UserProfile model (update: remove 'interests = models.TextField')
class UserProfile(models.Model):
    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='profile')

    full_name = models.CharField(max_length=200)
    gender = models.CharField(max_length=10)
    birthdate = models.DateField()
    bio = models.TextField(blank=True)

    job_title = models.CharField(max_length=100, blank=True)
    company = models.CharField(max_length=100, blank=True)
    education = models.CharField(max_length=100, blank=True)

    # ✅ Many-to-Many relation instead of free-text
    interests = models.ManyToManyField(Interest, related_name="user_profiles", blank=True)

    is_premium = models.BooleanField(default=False)
    premium_since = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.full_name



# Profile Photo model
class ProfilePhoto(models.Model):
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='photos')

    url = models.URLField()
    position = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_private = models.BooleanField(default=False)

    class Meta:
        ordering = ['position']

    def __str__(self):
        return f"Photo {self.id} for {self.user.username}"



