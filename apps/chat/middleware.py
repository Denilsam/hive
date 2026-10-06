from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs

User = get_user_model()


@database_sync_to_async
def get_user_from_jwt(token_string):
    try:
        access_token = AccessToken(token_string)
        user_id = access_token.get('user_id')
        user = User.objects.get(id=user_id)
        if user.is_active:
            return user
    except Exception:
        pass
    return AnonymousUser()


class JwtAuthMiddleware(BaseMiddleware):
    """
    Custom Channels middleware that authenticates WebSocket connections using JWT access tokens.
    Supports query parameter (?token=<access_token>) and Authorization header (Bearer <access_token>).
    Preserves existing session authentication if scope['user'] is already set.
    """
    async def __call__(self, scope, receive, send):
        existing_user = scope.get('user')
        if not existing_user or not existing_user.is_authenticated:
            token = None

            # 1. Query parameter: ?token=<access_token>
            query_string = scope.get('query_string', b'').decode('utf-8')
            query_params = parse_qs(query_string)
            if 'token' in query_params and query_params['token']:
                token = query_params['token'][0]

            # 2. Authorization Header: Bearer <access_token>
            if not token:
                headers = dict(scope.get('headers', []))
                auth_header = headers.get(b'authorization', b'').decode('utf-8')
                if auth_header.startswith('Bearer '):
                    token = auth_header.split('Bearer ')[1].strip()

            if token:
                scope['user'] = await get_user_from_jwt(token)

        return await super().__call__(scope, receive, send)


def JwtAuthMiddlewareStack(inner):
    from channels.auth import AuthMiddlewareStack
    return AuthMiddlewareStack(JwtAuthMiddleware(inner))
