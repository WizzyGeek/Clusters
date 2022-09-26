"""The aiohttp Server"""
from typing import (
    Union,
    Callable,
    NoReturn,
    Awaitable,
    Any,
    # Tuple,
    # List,
    Optional,
    Mapping,
    Dict,
    Literal
    # Sequence
)
import json as Json
import aiohttp

from aiohttp_apispec import (
    setup_aiohttp_apispec as setup_docs,
    validation_middleware
)

import aiohttp.web as Web
from aiohttp.web import middleware as Middleware, json_response as JsonResp # noqa
from marshmallow import Schema, ValidationError

from .auth import basic_auth_ware
from .routes import routes

def shard_logic(first: int, last: int, workers: int):  # see get_worker
    ids = list(range(first, last + 1))
    for i in range(workers):
        yield ids[::workers - i]
        del ids[::workers - i]


@Middleware
async def intercept_server_error(
        request: Web.Request,
        handler: Callable[[Web.Request], Awaitable[Union[Any, NoReturn]]]
        ) -> Union[Any, NoReturn]:
    try:
        return await handler(request)
    except Web.HTTPException:
        raise
    except Exception as err:
        raise Web.HTTPInternalServerError(reason="Unexpected Internal Error") from err


def validation_error_handler(
    error: ValidationError,
    req: Web.Request,
    schema: Schema,
    error_status_code: Optional[int] = None,
    error_headers: Optional[Mapping[str, str]] = None,
) -> NoReturn:
    raise Web.HTTPBadRequest(
            body=Json.dumps(error.messages),
            headers=error_headers,
            content_type="application/json",
        )


async def on_shutdown(app: Web.Application) -> None:
    for ws in app['Worker'].values():
        await ws.close(code=aiohttp.WSCloseCode.GOING_AWAY, message="Server Shutdown")


def setup(
        FirstShard: int, LastShard: int,
        workers: int, *,
        basic_auth_creds: Union[Dict[str, str], None] = None,
        encoder: Callable = Json.dumps, decoder: Callable = Json.loads) -> Web.Application:
    App = Web.Application()
    App["ShardRange"] = (FirstShard, LastShard)
    App["Shards"] = list(shard_logic(FirstShard, LastShard, workers))
    App["Workers"] = [None for _ in range(workers)]
    App["works"] = workers
    App["com.wiz.namespace"] = {"e": encoder, "d": decoder}
    if basic_auth_creds:
        App.middlewares.append(basic_auth_ware(basic_auth_creds))
    App.middlewares.extend([intercept_server_error, validation_middleware])
    App.on_shutdown.append(on_shutdown)
    setup_docs(App, error_callback=validation_error_handler)
    App.add_routes(routes)
    return App
