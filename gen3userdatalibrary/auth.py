from authutils.token.fastapi import access_token
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gen3authz.client.arborist.async_client import ArboristClient
from starlette.status import HTTP_401_UNAUTHORIZED as HTTP_401_UNAUTHENTICATED
from starlette.status import (
    HTTP_403_FORBIDDEN,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_503_SERVICE_UNAVAILABLE,
)

from gen3userdatalibrary import config, logging

get_bearer_token = HTTPBearer(auto_error=False)
arborist = ArboristClient()


async def authorize_request(
    authz_access_method: str = "access",
    authz_resources: list[str] = None,
    token: HTTPAuthorizationCredentials = None,
    request: Request = None,
):
    """
    Authorizes the incoming request based on the provided token and Arborist access policies.

    Args:
        authz_access_method (str): The Arborist access method to check (default is "access").
        authz_resources (list[str]): The list of resources to check against
        token (HTTPAuthorizationCredentials): an authorization token (optional, you can also provide request
            and this can be parsed from there). this has priority over any token from request.
        request (Request): The incoming HTTP request. Used to parse tokens from header.

    Raises:
        HTTPException: Raised if authorization fails.

    Note:
        If `DEBUG_SKIP_AUTH` is enabled
        and no token is provided, the check is also bypassed.
    """
    if config.DEBUG_SKIP_AUTH and not token:
        logging.warning(
            "DEBUG_SKIP_AUTH mode is on and no token was provided, BYPASSING authorization check"
        )
        return

    token = await _get_token(token, request)

    # either this was provided or we've tried to get it from the Bearer header
    if not token:
        raise HTTPException(status_code=HTTP_401_UNAUTHENTICATED)

    # try to get the ID so the debug log has more information
    try:
        user_id = await get_user_id(token, request)
    except HTTPException as exc:
        logging.debug(
            f"Unable to determine user_id. Defaulting to `Unknown`. Exc: {exc}"
        )
        user_id = "Unknown"

    is_authorized = False
    try:
        is_authorized = await arborist.auth_request(
            token.credentials,
            service="gen3_data_library",
            methods=authz_access_method,
            resources=authz_resources,
        )
    except Exception as exc:
        logging.error(f"arborist.auth_request failed, exc: {exc}")
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR) from exc

    if not is_authorized:
        logging.debug(
            f"user `{user_id}` does not have `{authz_access_method}` access "
            f"on `{authz_resources}`"
        )
        raise HTTPException(status_code=HTTP_403_FORBIDDEN)


async def get_user_id(
    token: HTTPAuthorizationCredentials = None, request: Request = None
):
    """
    Retrieves the user ID from the provided token/request

    Args:
        token (HTTPAuthorizationCredentials): an authorization token (optional, you can also provide request
            and this can be parsed from there). this has priority over any token from request.
        request (Request): The incoming HTTP request. Used to parse tokens from header.

    Returns:
        str: The user's ID.

    Raises:
        HTTPException: Raised if the token is missing or invalid.

    Note:
        If `DEBUG_SKIP_AUTH` is enabled and no token is provided, user_id is set to "0".
    """
    if config.DEBUG_SKIP_AUTH and not token:
        logging.warning(
            "DEBUG_SKIP_AUTH mode is on and no token was provided, RETURNING user_id = 0"
        )
        return 0

    token_claims = await _get_token_claims(token, request)
    if "sub" not in token_claims:
        raise HTTPException(status_code=HTTP_401_UNAUTHENTICATED)

    return token_claims["sub"]


async def _get_token_claims(
    token: HTTPAuthorizationCredentials = None,
    request: Request = None,
):
    """
    Retrieves and validates token claims from the provided token.

    Args:
        token (HTTPAuthorizationCredentials): an authorization token (optional, you can also provide request
            and this can be parsed from there). this has priority over any token from request.
        request (Request): The incoming HTTP request. Used to parse tokens from header.

    Returns:
        dict: The token claims.

    Raises:
        HTTPException: Raised if the token is missing or invalid.
    """
    token = await _get_token(token, request)
    # either this was provided or we've tried to get it from the Bearer header
    if not token:
        raise HTTPException(status_code=HTTP_401_UNAUTHENTICATED)

    # This is what the Gen3 AuthN/Z service adds as the audience to represent Gen3 services
    if request:
        audience = f"https://{request.base_url.netloc}/user"
    else:
        logging.warning(
            "Unable to determine expected audience b/c request context was not provided... setting audience to `None`."
        )
        audience = None

    try:
        # NOTE: token can be None if no Authorization header was provided, we expect
        #       this to cause a downstream exception since it is invalid
        logging.debug(
            f"checking access token for scopes: `user` and `openid` and audience: `{audience}`"
        )
        token_claims = await access_token(
            "user", "openid", audience=audience, purpose="access"
        )(token)
    except Exception as exc:
        logging.error(exc.detail if hasattr(exc, "detail") else exc, exc_info=True)
        raise HTTPException(
            HTTP_401_UNAUTHENTICATED,
            "Could not verify, parse, and/or validate scope from provided access token.",
        ) from exc

    return token_claims


async def _get_token(token, request):
    """
    Retrieves the token from the request's Bearer header or if there's no request, returns token

    Args:
        token (HTTPAuthorizationCredentials): The provided token, if available.
        request (Request): The incoming HTTP request.

    Returns:
        The obtained token.
    """
    if not token:
        # we need a request in order to get a bearer token
        if request:
            token = await get_bearer_token(request)
    return token
