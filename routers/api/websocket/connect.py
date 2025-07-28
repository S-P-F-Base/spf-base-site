import asyncio

from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
)

from data_control import WebSocketManager, req_authorization_websocket

router = APIRouter()


@router.websocket("/connect")
async def websocket_auth(websocket: WebSocket):
    await websocket.accept()
    username = None

    try:
        await websocket.send_text("auth request")

        try:
            token = await asyncio.wait_for(websocket.receive_text(), timeout=10.0)
        except asyncio.TimeoutError:
            await websocket.close(code=1008)
            return

        if not token:
            await websocket.close(1008)
            return

        username = req_authorization_websocket(token)
        if not username:
            await websocket.close(code=1008)
            return

        await WebSocketManager.connect(username, websocket)

        while True:
            alive = await WebSocketManager.heartbeat(websocket)
            if not alive:
                await websocket.close(code=1001)
                break

            await asyncio.sleep(60)

    except WebSocketDisconnect:
        pass

    finally:
        if username:
            WebSocketManager.disconnect(username)
