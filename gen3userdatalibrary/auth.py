from typing import Any, Optional, Union

from authutils.token.fastapi import access_token
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from gen3authz.client.arborist.async_client import ArboristClient
from gen3authz.client.arborist.errors import ArboristError
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED as HTTP_401_UNAUTHENTICATED
from starlette.status import HTTP_403_FORBIDDEN, HTTP_500_INTERNAL_SERVER_ERROR

from gen3userdatalibrary import config, logging

get_bearer_token = HTTPBearer(auto_error=False)
arborist = ArboristClient()

get_user_data_library_endpoint = lambda user_id: f"/users/{user_id}/user-data-library"
get_lists_endpoint = lambda user_id: f"/users/{user_id}/user-data-library/lists"
get_list_by_id_endpoint = (
    lambda user_id, list_id: f"/users/{user_id}/user-data-library/lists/{list_id}"
)


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
        logging.info(
            f"Unable to determine user_id. Defaulting to `Unknown`. Exc: {exc}"
        )
        user_id = "Unknown"
    is_authorized = await arborist.auth_request(
        token.credentials,
        service="gen3_user_data_library",
        methods=authz_access_method,
        resources=authz_resources,
    )

    if not is_authorized:
        try:
            # Create the policy (in case it didn't exist for the auth_request), then retry
            username = await get_username(token, request)
            logging.debug(f"Attempting to create policy for user {user_id}...")
            await create_user_policy(
                user_id=user_id, username=username, arborist_client=arborist
            )

            logging.debug("Retrying authz request...")

            is_authorized = await arborist.auth_request(
                token.credentials,
                service="gen3_user_data_library",
                methods=authz_access_method,
                resources=authz_resources,
            )
            if not is_authorized:
                logging.info(
                    f"user `{user_id}` does not have `{authz_access_method}` access "
                    f"on `{authz_resources}`"
                )
                raise HTTPException(status_code=HTTP_403_FORBIDDEN)
        except ArboristError as exc:
            logging.error(f"arborist request failed, exc: {exc}")
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR) from exc


async def get_user_id(
    token: HTTPAuthorizationCredentials = None, request: Request = None
) -> Union[int, Any]:
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
        return "0"

    token_claims = await _get_token_claims(token, request)
    if "sub" not in token_claims:
        return "Unknown"

    return token_claims["sub"]


async def get_username(
    token: HTTPAuthorizationCredentials = None, request: Request = None
) -> Union[int, Any]:
    """
    Retrieves the username from the provided token/request

    Args:
        token (HTTPAuthorizationCredentials): an authorization token (optional, you can also provide request
            and this can be parsed from there). this has priority over any token from request.
        request (Request): The incoming HTTP request. Used to parse tokens from header.

    Returns:
        str: The user's username.

    Raises:
        HTTPException: Raised if the token is missing or invalid.

    Note:
        If `DEBUG_SKIP_AUTH` is enabled and no token is provided, username is set to "librarian".
    """
    if config.DEBUG_SKIP_AUTH and not token:
        logging.warning(
            "DEBUG_SKIP_AUTH mode is on and no token was provided, RETURNING username = 'librarian'"
        )
        return "0"

    token_claims = await _get_token_claims(token, request)
    if "user" not in token_claims.get("context", {}):
        raise HTTPException(status_code=HTTP_401_UNAUTHENTICATED)

    username = token_claims["context"]["user"]["name"]
    return username


async def _get_token_claims(
    token: HTTPAuthorizationCredentials = None,
    request: Request = None,
) -> dict:
    """
    Retrieves and validates token claims from the provided token.

    handler for proccessing token

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
        return {"context": {"name": "Unknown"}, "sub": "Unknown"}

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
        g = access_token("user", "openid", audience=audience, purpose="access")
        token_claims = await g(token)
    except Exception as exc:
        logging.error(exc.detail if hasattr(exc, "detail") else exc, exc_info=True)
        raise HTTPException(
            HTTP_401_UNAUTHENTICATED,
            "Could not verify, parse, and/or validate scope from provided access token.",
        ) from exc

    return token_claims


async def _get_token(
    token: Union[HTTPAuthorizationCredentials, str], request: Optional[Request]
):
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


async def create_user_policy(
    user_id: str, username: str, arborist_client: ArboristClient
):
    """
    Creates the user policy necessary for a user to maintain lists in their data library.
    Args:
        user_id (str): id of the user
        username (str): username of the user
        arborist_client (ArboristClient): client for sending requests to arborist.
    """
    resource = get_lists_endpoint(user_id)
    is_resource_assigned_to_user = False
    try:
        resources = await arborist_client.list_resources_for_user(username)
        logging.info(
            f"Found user's data-library assigned to user in arborist, skipping policy generation"
        )
        is_resource_assigned_to_user = resource in set(resources)
    except ArboristError as e:
        if e.code == 404:
            logging.info(
                f"Unable to find {username} in arborist, creating and setting up data-library policy"
            )
        else:
            raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR) from e

    if is_resource_assigned_to_user:
        return

    await arborist_client.create_user_if_not_exist(username)
    logging.info(f"Policy does not exist for user_id {user_id}")
    role_ids = ["create", "read", "update", "delete"]

    logging.info("Attempting to create arborist resource: {}".format(resource))
    await arborist_client.update_resource(
        path="/",
        resource_json={
            "name": resource,
            "description": f"Library for user_id {user_id}",
        },
        merge=True,
        create_parents=True,
    )

    policy_json = {
        "id": user_id,
        "description": "policy created by gen3-user-data-library",
        "role_ids": role_ids,
        "resource_paths": [resource],
    }

    logging.info(f"Policy {user_id} does not exist, attempting to create....")

    await arborist_client.update_policy(
        policy_id=user_id, policy_json=policy_json, create_if_not_exist=True
    )

    logging.info(
        f"Granting resource {resource} to {username} with policy_id {user_id}...."
    )

    await arborist_client.grant_user_policy(username=username, policy_id=user_id)
