from django.contrib.auth.backends import ModelBackend


class AllowInactiveModelBackend(ModelBackend):
    """
    Custom authentication backend that allows inactive users to authenticate.
    This is necessary so that our LoginView can catch unverified (inactive)
    users and display a helpful verification resend warning instead of a generic
    'invalid credentials' error.
    """
    def user_can_authenticate(self, user):
        # Allow inactive users to authenticate
        return True
