from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.profiles.models import Skill


class Collaboration(models.Model):
    class ProjectType(models.TextChoices):
        STARTUP = 'STARTUP', 'Startup'
        COLLEGE_PROJECT = 'COLLEGE_PROJECT', 'College Project'
        FREELANCE = 'FREELANCE', 'Freelance'
        OPEN_SOURCE = 'OPEN_SOURCE', 'Open Source'
        PERSONAL_PROJECT = 'PERSONAL_PROJECT', 'Personal Project'

    class BudgetType(models.TextChoices):
        PAID = 'PAID', 'Paid'
        UNPAID = 'UNPAID', 'Unpaid'
        EQUITY = 'EQUITY', 'Equity'
        NEGOTIABLE = 'NEGOTIABLE', 'Negotiable'

    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Open'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        CLOSED = 'CLOSED', 'Closed'

    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='collaborations'
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    category = models.CharField(max_length=100) # e.g. Web Development, UI/UX, etc.
    project_type = models.CharField(
        max_length=30,
        choices=ProjectType.choices,
        default=ProjectType.PERSONAL_PROJECT
    )
    budget_type = models.CharField(
        max_length=20,
        choices=BudgetType.choices,
        default=BudgetType.UNPAID
    )
    budget_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True
    )
    duration = models.CharField(max_length=100, blank=True, null=True) # e.g. "2 Months"
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} by {self.creator.email}"


class CollaborationSkill(models.Model):
    collaboration = models.ForeignKey(
        Collaboration,
        on_delete=models.CASCADE,
        related_name='required_skills'
    )
    skill = models.ForeignKey(
        Skill,
        on_delete=models.CASCADE,
        related_name='collaboration_skills'
    )

    class Meta:
        unique_together = ('collaboration', 'skill')

    def __str__(self):
        return f"{self.skill.name} for {self.collaboration.title}"


class CollaborationApplication(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        ACCEPTED = 'ACCEPTED', 'Accepted'
        REJECTED = 'REJECTED', 'Rejected'
        WITHDRAWN = 'WITHDRAWN', 'Withdrawn'

    collaboration = models.ForeignKey(
        Collaboration,
        on_delete=models.CASCADE,
        related_name='applications'
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='marketplace_applications'
    )
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('collaboration', 'applicant')
        ordering = ['-created_at']

    def clean(self):
        super().clean()
        if self.collaboration.creator == self.applicant:
            raise ValidationError("You cannot apply to your own project opportunity.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Application by {self.applicant.email} to {self.collaboration.title}"
