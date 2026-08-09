from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """
    Generate unique, temporary tokens for email verification URLs.
    """
    def _make_hash_value(self, user, timestamp):
        # Including is_verified ensures that as soon as the user is verified,
        # the token becomes invalid.
        return (
            str(user.pk) + str(timestamp) + str(user.is_verified)
        )


email_verification_token = EmailVerificationTokenGenerator()
