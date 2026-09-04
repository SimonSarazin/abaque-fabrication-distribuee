import hashlib

from django.contrib.auth import get_user_model
from mozilla_django_oidc.auth import OIDCAuthenticationBackend


class AbaqueOIDCBackend(OIDCAuthenticationBackend):
    """Map an OIDC identity to one local Django user."""

    def filter_users_by_claims(self, claims):
        email = claims.get("email")
        if not email:
            return get_user_model().objects.none()
        return get_user_model().objects.filter(email__iexact=email)

    def get_username(self, claims):
        username = claims.get("preferred_username") or claims.get("email") or claims.get("sub")
        username = username[:150]
        user_model = get_user_model()
        if not user_model.objects.filter(username=username).exists():
            return username

        suffix_source = claims.get("sub") or claims.get("email") or username
        suffix = hashlib.sha256(suffix_source.encode()).hexdigest()[:10]
        candidate = f"{username[:139]}-{suffix}"
        counter = 2
        while user_model.objects.filter(username=candidate).exists():
            candidate = f"{username[:137]}-{suffix}-{counter}"
            counter += 1
        return candidate

    def create_user(self, claims):
        user = super().create_user(claims)
        user.email = claims.get("email", "")
        user.save(update_fields=["email"])
        return user

    def update_user(self, user, claims):
        user.email = claims.get("email", user.email)
        user.save(update_fields=["email"])
        return user