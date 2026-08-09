from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


def validate_image_size(value):
    """
    Validator to restrict uploaded files to 2MB.
    """
    if value.size > 2 * 1024 * 1024:
        raise ValidationError("The maximum file size allowed is 2MB.")
    return value


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    profile_image = models.ImageField(
        upload_to='profiles/avatars/',
        validators=[validate_image_size],
        blank=True,
        null=True
    )
    cover_image = models.ImageField(
        upload_to='profiles/covers/',
        validators=[validate_image_size],
        blank=True,
        null=True
    )
    headline = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    location = models.CharField(max_length=150, blank=True, null=True)
    
    # Social links
    website = models.URLField(blank=True, null=True)
    github_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def completion_percentage(self):
        """
        Calculate and return the completion percentage of the profile (0-100%).
        """
        percentage = 0
        # Profile image: 10%
        if self.profile_image:
            percentage += 10
        # Cover image: 5%
        if self.cover_image:
            percentage += 5
        # Headline: 15%
        if self.headline and self.headline.strip():
            percentage += 15
        # Bio: 15%
        if self.bio and self.bio.strip():
            percentage += 15
        # Location: 10%
        if self.location and self.location.strip():
            percentage += 10
        # Skills (at least one UserSkill mapped to the user): 15%
        if self.user.userskill_set.exists():
            percentage += 15
        # Education (at least one record): 10%
        if self.user.education_set.exists():
            percentage += 10
        # Experience (at least one record): 10%
        if self.user.experience_set.exists():
            percentage += 10
        # Social links (at least one social link URL populated): 10%
        if (self.website and self.website.strip()) or \
           (self.github_url and self.github_url.strip()) or \
           (self.linkedin_url and self.linkedin_url.strip()) or \
           (self.twitter_url and self.twitter_url.strip()):
            percentage += 10
        return percentage

    def __str__(self):
        return f"Profile of {self.user.email}"


class Education(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='education_set'
    )
    degree = models.CharField(max_length=150)
    institution = models.CharField(max_length=150)
    field_of_study = models.CharField(max_length=150)
    start_year = models.IntegerField()
    end_year = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    def clean(self):
        if self.end_year and self.start_year > self.end_year:
            raise ValidationError("Start year cannot be after end year.")

    def __str__(self):
        return f"{self.degree} at {self.institution} ({self.user.email})"


class Experience(models.Model):
    class EmploymentType(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Full Time'
        PART_TIME = 'PART_TIME', 'Part Time'
        INTERNSHIP = 'INTERNSHIP', 'Internship'
        FREELANCE = 'FREELANCE', 'Freelance'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='experience_set'
    )
    company_name = models.CharField(max_length=150)
    role = models.CharField(max_length=150)
    employment_type = models.CharField(
        max_length=20,
        choices=EmploymentType.choices,
        default=EmploymentType.FULL_TIME
    )
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    currently_working = models.BooleanField(default=False)
    description = models.TextField(blank=True, null=True)

    def clean(self):
        if self.currently_working:
            self.end_date = None
        elif not self.end_date:
            raise ValidationError("End date is required if you are not currently working there.")
        
        if self.end_date and self.start_date > self.end_date:
            raise ValidationError("Start date cannot be after end date.")

    def __str__(self):
        return f"{self.role} at {self.company_name} ({self.user.email})"


class Skill(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class UserSkill(models.Model):
    class SkillLevel(models.TextChoices):
        BEGINNER = 'BEGINNER', 'Beginner'
        INTERMEDIATE = 'INTERMEDIATE', 'Intermediate'
        ADVANCED = 'ADVANCED', 'Advanced'
        EXPERT = 'EXPERT', 'Expert'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='userskill_set'
    )
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.CharField(
        max_length=20,
        choices=SkillLevel.choices,
        default=SkillLevel.INTERMEDIATE
    )

    class Meta:
        unique_together = ('user', 'skill')

    def __str__(self):
        return f"{self.user.email} - {self.skill.name} ({self.level})"


class Certificate(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='certificate_set'
    )
    title = models.CharField(max_length=150)
    organization = models.CharField(max_length=150)
    issue_date = models.DateField()
    certificate_url = models.URLField(blank=True, null=True)
    certificate_file = models.FileField(
        upload_to='certificates/',
        validators=[validate_image_size],
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.title} from {self.organization} ({self.user.email})"
