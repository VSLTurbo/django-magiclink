from datetime import timedelta
from uuid import uuid4

from django.conf import settings as djsettings
from django.contrib.auth import get_user_model
from django.db.utils import IntegrityError
from django.http import HttpRequest
from django.utils import timezone
from django.utils.crypto import get_random_string

from . import settings
from .models import MagicLink, MagicLinkError
from .utils import get_client_ip, get_url_path


def create_magiclink(
    email: str,
    request: HttpRequest | None = None,
    redirect_url: str = '',
    expiry: timezone.datetime | None = None,
    email_ignore_case: bool | None = None,
    login_request_time_limit: int | None = None,
    one_token_per_user: bool | None = None,
    require_same_ip: bool | None = None,
    anonymize_ip: bool | None = None,
    auth_timeout: int | None = None,
    token_length: int | None = None,
) -> MagicLink:
    if email_ignore_case is None:
        email_ignore_case = settings.EMAIL_IGNORE_CASE
    if login_request_time_limit is None:
        login_request_time_limit = settings.LOGIN_REQUEST_TIME_LIMIT
    if one_token_per_user is None:
        one_token_per_user = settings.ONE_TOKEN_PER_USER
    if require_same_ip is None:
        require_same_ip = settings.REQUIRE_SAME_IP
    if anonymize_ip is None:
        anonymize_ip = settings.ANONYMIZE_IP
    if auth_timeout is None:
        auth_timeout = settings.AUTH_TIMEOUT
    if token_length is None:
        token_length = settings.TOKEN_LENGTH

    if email_ignore_case:
        email = email.lower()

    if login_request_time_limit > 0:
        limit = timezone.now() - timedelta(seconds=login_request_time_limit)  # NOQA: E501
        over_limit = MagicLink.objects.filter(email=email, created__gte=limit)
        if over_limit:
            raise MagicLinkError('Muitas requisições de login para esse email. Aguarde e tente novamente.')

    if one_token_per_user:
        magic_links = MagicLink.objects.filter(email=email, disabled=False)
        magic_links.update(disabled=True)

    if not redirect_url:
        redirect_url = get_url_path(djsettings.LOGIN_REDIRECT_URL)

    client_ip = None

    if require_same_ip and request is not None:
        client_ip = get_client_ip(request)
        if client_ip and anonymize_ip:
            client_ip = client_ip[:client_ip.rfind('.')+1] + '0'

    if expiry is None:
        expiry = timezone.now() + timedelta(seconds=auth_timeout)

    magic_link = MagicLink.objects.create(
        email=email,
        token=get_random_string(length=token_length),
        expiry=expiry,
        redirect_url=redirect_url,
        cookie_value=str(uuid4()),
        ip_address=client_ip,
    )
    return magic_link


def get_or_create_user(
    email: str,
    username: str = '',
    first_name: str = '',
    last_name: str = ''
):
    User = get_user_model()

    if settings.EMAIL_IGNORE_CASE:
        email = email.lower()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        pass
    else:
        return user

    user_fields = [field.name for field in User._meta.get_fields()]

    if not username and settings.EMAIL_AS_USERNAME:
        username = email

    user_details = {'email': email}
    if 'first_name' in user_fields and first_name:
        user_details['first_name'] = first_name
    if 'last_name' in user_fields and last_name:
        user_details['last_name'] = last_name
    if 'full_name' in user_fields:
        user_details['full_name'] = f'{first_name} {last_name}'.strip()
    if 'name' in user_fields:
        user_details['name'] = f'{first_name} {last_name}'.strip()

    if 'username' in user_fields and not username:
        # Set a random username if we need to set a username and
        # EMAIL_AS_USERNAME is False
        created = False
        while not created:
            user_details['username'] = get_random_string(length=10)
            try:
                user = User.objects.create(**user_details)
                created = True
            except IntegrityError:  # pragma: no cover
                pass
    else:
        if 'username' in user_fields:
            user_details['username'] = username
        user = User.objects.create(**user_details)

    return user