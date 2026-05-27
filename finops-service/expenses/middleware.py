"""
JWT Authentication Middleware (ASR 2 - Security)

Validates Auth0 JWT tokens and enforces role-based access control.
- Checks for valid JWT with RS256 signature from Auth0
- Verifies the user has the 'finops' or 'admin' role
- Returns 403 Forbidden for unauthorized access
- Logs all access attempts to AuditLog for audit trail
- Target: <50ms overhead on top of query latency
"""
import time
import json
import logging
import urllib.request
from functools import lru_cache

import jwt
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger('audit')

# Routes that require role validation
PROTECTED_ROUTES = [
    '/finops/expenses/by-area/',
]

# Routes excluded from auth (health checks, etc.)
PUBLIC_ROUTES = [
    '/finops/health/',
]


@lru_cache(maxsize=1)
def get_auth0_public_key():
    """Fetch and cache Auth0 JWKS public keys."""
    jwks_url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    with urllib.request.urlopen(jwks_url, timeout=5) as resp:
        return json.loads(resp.read())


class JWTAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path_info

        # Skip auth for public routes
        if any(path.startswith(pub) for pub in PUBLIC_ROUTES):
            return self.get_response(request)

        # Only enforce on protected routes
        if any(path.startswith(prot) for prot in PROTECTED_ROUTES):
            start_time = time.time()
            auth_result = self._validate_request(request)
            auth_latency_ms = (time.time() - start_time) * 1000

            if not auth_result['authorized']:
                self._log_audit(
                    action=auth_result['action'],
                    endpoint=path,
                    user_sub=auth_result.get('sub'),
                    user_roles=auth_result.get('roles', []),
                    ip_address=self._get_client_ip(request),
                    reason=auth_result['reason'],
                )
                return JsonResponse(
                    {
                        'error': 'Forbidden',
                        'message': auth_result['reason'],
                        'auth_latency_ms': round(auth_latency_ms, 2),
                    },
                    status=403,
                )

            request.jwt_payload = auth_result['payload']
            request.user_roles = auth_result['roles']

        return self.get_response(request)

    def _validate_request(self, request):
        """Validate JWT token and check roles."""
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return {
                'authorized': False,
                'action': 'MISSING_TOKEN',
                'reason': 'Authorization header missing or malformed',
            }

        token = auth_header.split(' ')[1]

        try:
            # Decode header to get kid
            unverified_header = jwt.get_unverified_header(token)
            jwks = get_auth0_public_key()

            # Find matching key
            rsa_key = {}
            for key in jwks['keys']:
                if key['kid'] == unverified_header.get('kid'):
                    rsa_key = {
                        'kty': key['kty'],
                        'kid': key['kid'],
                        'use': key['use'],
                        'n': key['n'],
                        'e': key['e'],
                    }
                    break

            if not rsa_key:
                return {
                    'authorized': False,
                    'action': 'INVALID_TOKEN',
                    'reason': 'Unable to find matching public key',
                }

            # Verify token
            payload = jwt.decode(
                token,
                jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(rsa_key)),
                algorithms=['RS256'],
                audience=settings.AUTH0_AUDIENCE,
                issuer=f"https://{settings.AUTH0_DOMAIN}/",
            )

            # Extract roles from token claims
            # Auth0 stores custom claims under a namespace
            roles_claim = f"https://bite.co/roles"
            roles = payload.get(roles_claim, [])
            if not roles:
                roles = payload.get('roles', [])

            sub = payload.get('sub', 'unknown')

            # Check required roles
            has_required_role = any(
                role in settings.REQUIRED_ROLES for role in roles
            )

            if not has_required_role:
                return {
                    'authorized': False,
                    'action': 'INSUFFICIENT_ROLE',
                    'reason': f'Required roles: {settings.REQUIRED_ROLES}. User roles: {roles}',
                    'sub': sub,
                    'roles': roles,
                }

            return {
                'authorized': True,
                'payload': payload,
                'sub': sub,
                'roles': roles,
            }

        except jwt.ExpiredSignatureError:
            return {
                'authorized': False,
                'action': 'INVALID_TOKEN',
                'reason': 'Token has expired',
            }
        except jwt.InvalidTokenError as e:
            return {
                'authorized': False,
                'action': 'INVALID_TOKEN',
                'reason': f'Invalid token: {str(e)}',
            }

    def _log_audit(self, action, endpoint, user_sub, user_roles, ip_address, reason):
        """Persist audit log entry for security monitoring."""
        try:
            from expenses.models import AuditLog
            AuditLog.objects.create(
                action=action,
                endpoint=endpoint,
                user_sub=user_sub,
                user_roles=user_roles or [],
                ip_address=ip_address,
                reason=reason,
            )
            logger.info(
                f"AUDIT | {action} | sub={user_sub} | endpoint={endpoint} | reason={reason}"
            )
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
