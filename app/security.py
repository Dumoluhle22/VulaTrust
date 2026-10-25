"""Request protection (issue 20): CSRF tokens, security headers, size limit.

CSRF (cross-site request forgery) is when another website tricks your browser
into submitting a form to this app. The defence here is the "double-submit
cookie" pattern: every page sets a random token in a cookie and puts the same
token in each form. A POST is accepted only when the two match, which a
foreign website cannot arrange. The cookie is also SameSite=Strict.

Set VULATRUST_CSRF=0 to switch the check off. The tests do this, except the
tests that are about CSRF.
"""
import os
import re
import secrets

from fastapi import Request
from fastapi.responses import PlainTextResponse

from app.csv_import import MAX_FILE_BYTES
from app.templating import templates

COOKIE_NAME = "vulatrust_csrf"
FIELD_NAME = "csrf_token"
MAX_REQUEST_BYTES = MAX_FILE_BYTES + 262_144   # the file limit plus room for form fields
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_TOKEN_FORMAT = re.compile(r"^[A-Za-z0-9_-]{32,128}$")

SECURITY_HEADERS = {
    # No scripts anywhere. Inline styles are allowed because the pages carry a small <style> block.
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'none'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",   # these pages show business records
}


class CsrfError(Exception):
    """Raised when a form post does not carry a valid CSRF token."""


def csrf_enabled() -> bool:
    return os.getenv("VULATRUST_CSRF", "1") != "0"


async def require_csrf(request: Request) -> None:
    """A dependency applied to every route. Only unsafe methods are checked."""
    if request.method not in UNSAFE_METHODS or not csrf_enabled():
        return
    cookie = request.cookies.get(COOKIE_NAME, "")
    form = await request.form()  # cached, so the route can read it again
    submitted = str(form.get(FIELD_NAME) or "")
    if (
        not _TOKEN_FORMAT.match(cookie)
        or not submitted
        or not secrets.compare_digest(cookie.encode(), submitted.encode())
    ):
        raise CsrfError()


async def csrf_error_page(request: Request, _exc: CsrfError):
    response = templates.TemplateResponse(
        request,
        "error.html",
        {
            "title": "Request could not be verified",
            "message": (
                "The form could not be verified, so nothing was changed. "
                "Go back, reload the page and try again."
            ),
        },
        status_code=403,
    )
    _add_headers(response)
    return response


def _add_headers(response) -> None:
    for name, value in SECURITY_HEADERS.items():
        response.headers[name] = value


async def security_middleware(request: Request, call_next):
    length = request.headers.get("content-length", "")
    if length.isdigit() and int(length) > MAX_REQUEST_BYTES:
        response = PlainTextResponse("The request is too large.", status_code=413)
        _add_headers(response)
        return response

    token = request.cookies.get(COOKIE_NAME, "")
    is_new = not _TOKEN_FORMAT.match(token)
    if is_new:
        token = secrets.token_urlsafe(32)
    request.state.csrf_token = token  # templates put this in every form

    response = await call_next(request)
    if is_new:
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", path="/")
    _add_headers(response)
    return response
