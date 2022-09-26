from typing import (
    Dict,
    Callable,
    Awaitable,
    Union,
    NoReturn,
    Any
)

import aiohttp.web as Web
from aiohttp import BasicAuth

Middleware = Web.middleware


def basic_auth_ware(
    keys: Dict[str, str],
    encoding: str = "utf-8") -> Callable[
        [Web.Request,
            Callable[[Web.Request], Awaitable[Union[Any, NoReturn]]]],
        Awaitable[Union[Any, NoReturn]]]:
    """Generates Middle ware based on provided key(s)

    Parameters
    ----------
    key : Dict[str, str]
        The user to key mapping

    """
    if not isinstance(keys, dict):
        raise TypeError(f"Expected type dict, instead got {type(keys)}")

    for i in keys:
        if ":" in i:
            raise ValueError(f'Invalid login, "{i}". A ":" is not allowed in login (RFC 1945#section-11.1)')

    @Middleware
    async def BasicAuthWare(
            request: Web.Request,
            handler: Callable[
                [Web.Request],
                Awaitable[Union[Any, NoReturn]]]) -> Union[Any, NoReturn]:
        try:
            creds = BasicAuth.decode(
                request.headers.get('Authorization', ""),
                encoding=encoding)
        except ValueError as err:
            raise Web.HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic'}) from err

        if keys.get(creds.login, None) == creds.password:
            return await handler(request)
        else:
            raise Web.HTTPUnauthorized(headers={'WWW-Authenticate': 'Basic'})

    # Uncomment to remove decorator
    # BasicAuthWare.__middleware_version__ = 1

    return BasicAuthWare
