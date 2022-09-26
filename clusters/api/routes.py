import asyncio
from typing import Any, Awaitable, Type, Union, NoReturn, List, Optional

import aiohttp.web as Web
from aiohttp_apispec import (
    docs as Docs,
    # request_schema as ReqSchema,
    # response_schema as RespSchema, # noqa
)
from marshmallow import Schema, fields

routes = Web.RouteTableDef()

# class GatewaySchema(Schema):
#     worker_id = fields.Int(
#         description=(
#             "The id of the worker which was provide earlier,"
#             " null if connecting first time"),
#         allow_none=True)


# This returns the virtual ID it does not do any verification
def get_worker(shard: int, first: int, workers: int):
    """Returns the virtual worker ID of a shard

    Parameters
    ----------
    shard : int
        The shard whose worker needs to be fetched
    first : int
        The first shard ID registered on the cluster
    workers : int
        The number of workers on the cluter

    Returns
    -------
    int
        The Id of the worker which hosts the specified shard.
    """
    return (shard - (first % workers)) % workers


# I think this is better than using a Future for a constant result
async def none(): pass


def send_worker_json(
        app: Web.Application,
        worker: int, data: Any) -> Awaitable[None]:
    if (ws := app["Workers"][worker]):
        return ws.send_json(data)
    return none()


def send_each_json(app: Web.Application, data: dict) -> Awaitable[List[None]]:
    return asyncio.gather(*[ws.send_json(data) for ws in app["Workers"].values() if ws])


async def process_data(app: Web.Application, data: Any) -> None:
    worker, shard = data["to"].split(":")  # Array of 2 strings
    if worker == "*":
        if shard == "*":  # i.e -> {"to": "*:*"}
            await send_each_json(app, data)
        else:
            # This allows us to send stuff to a specific
            # worker who holds the shard
            await send_worker_json(
                app,
                get_worker(shard, app["ShardRange"][0], len(app["Workers"])),
                data)
    else:  # Else send the stuff to the worker
        await send_worker_json(app, int(worker), data)

@routes.get("/")
@Docs(
    summary="A websocket connection where every bot must connect to.",
    description=(
        "Shard IDs will be sent through this endpoint when the API is ready.")
)
async def gateway(
        request: Web.Request) -> Union[NoReturn, Web.WebSocketResponse]:
    ws = Web.WebSocketResponse()
    await ws.prepare(request)

    ID: Optional[int]
    try:
        ID = int(request.headers.get("ID")) # type: ignore
    except (TypeError, ValueError):
        ID = None
    workers: List[Web.WebSocketResponse] = request.app["Workers"]

    if ID is None:
        workers.append(ws)
        ID = workers.index(ws)
    else:
        try:
            _ws = workers[ID]
        except IndexError:
            workers.append(ws)
            ID = workers.index(ws)
        else:
            if _ws is None:
                workers[ID] = ws
            else:
                # This should not be excuted but ok.
                await ws.send_json({"e": "INVALID ID", "d": {"id": ID, "new_id": None}})
                await ws.close(code=1000, message=b"Invalid worker id")

    await ws.send_json({
            "e": "READY",
            "d": {
                "worker_id": ID,
                "workers": request.app["works"],
                "shard_range": request.app["Shardrange"],
                "shards": request.app["Shards"][ID]
            }
        })

    try:
        async for msg in ws:
            await process_data(request.app, msg.json())
    finally:
        # This alllows the worker to reconnect
        request.app["Workers"][ID] = None
        await send_each_json(request.app, {"to": "*:*", "e": "WORKER_DISCONNECT", "d": {"id": ID, "shards": request.app["Shards"][ID]}})

    return ws
