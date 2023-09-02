from django.contrib.auth.models import User
from django.db import models

from django.dispatch import receiver
from django.urls import reverse
from django_rest_passwordreset.signals import reset_password_token_created
from django.core.mail import send_mail


@receiver(reset_password_token_created)
def password_reset_token_created(sender, instance, reset_password_token, *args, **kwargs):
    email_plaintext_message = "{}?token={}".format(reverse('password_reset:reset-password-request'),
                                                   reset_password_token.key)

    send_mail(
        # title:
        "Password Reset for {title}".format(title="Some website title"),
        # message:
        email_plaintext_message,
        # from:
        "noreply@somehost.local",
        # to:
        [reset_password_token.user.email]
    )


class Profile(models.Model):
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE, related_name='profile')

    image = models.ImageField(default=None, blank=True, null=True, upload_to="images/", max_length=1000)
    address = models.CharField(max_length=255, default=None, null=True, blank=True)

    pro_status = models.BooleanField(default=False)
    pro_code = models.IntegerField(default=0)
    numberdesigns = models.IntegerField(default=0)
    paymentvertfication = models.BooleanField(default=False)
    trial_status = models.BooleanField(default=False)

    SUBSCRIPTION_CHOICES = (
        ('Free', 'Free'),
        ('Basic', 'Basic'),
        ('Booster', 'Booster'),
        ('Accelerate', 'Accelerate'),
        ('Professional', 'Professional'),
        ('Unlimited', 'Unlimited'),
    )

    subscription_plan = models.CharField(max_length=255, choices=SUBSCRIPTION_CHOICES, default='Free')

    designs_remaining = models.IntegerField(default=30)  # Initialize with 0
    plan_start_date = models.DateField(null=True, blank=True)
    plan_end_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        # Determine the initial designs_remaining value based on the subscription plan
        initial_designs_remaining = 0

        if self.subscription_plan == 'Free':
            initial_designs_remaining = 30
        elif self.subscription_plan == 'Basic':
            initial_designs_remaining = 50
        elif self.subscription_plan == 'Booster':
            initial_designs_remaining = 250
        elif self.subscription_plan == 'Accelerate':
            initial_designs_remaining = 850
        elif self.subscription_plan == 'Professional':
            initial_designs_remaining = 2000
        elif self.subscription_plan == 'Unlimited':
            initial_designs_remaining = -1  # Unlimited

        # Update designs_remaining if the subscription plan changes
        if self.pk is not None:
            # Check if the subscription plan has changed
            previous_profile = Profile.objects.get(pk=self.pk)
            if previous_profile.subscription_plan != self.subscription_plan:
                self.designs_remaining = initial_designs_remaining

        super(Profile, self).save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# show how we want it to be displayed

class CreatedDesign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=1)  # Set the default user ID
    desc = models.TextField()
    number = models.IntegerField()
    image = models.CharField(max_length=1000, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # Add the cre

    def __str__(self):
        return str(self.id)


class SavedDesign(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    design = models.ForeignKey(CreatedDesign, on_delete=models.CASCADE)
    status = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "design",)

    def __str__(self):
        return f"{self.user} - {self.task}"

