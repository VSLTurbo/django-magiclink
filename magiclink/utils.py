from django.http import HttpRequest
from django.urls import reverse
from django.urls.exceptions import NoReverseMatch


def get_client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_url_path(url: str) -> str:
    """
    url can either be a url name or a url path. First try and reverse a URL,
    if this does not exist then assume it's a url path
    """
    try:
        return reverse(url)
    except NoReverseMatch:
        return url

def mask_email(email: str) -> str | None:
    if not email:
        return None
    if email.find('@') == -1:
        return email[:3] + '*' * (len(email) - 3)
    email_parts = email.split('@')
    return email_parts[0][:3] + '*' * (len(email_parts[0]) - 3) + '@' + email_parts[1]
