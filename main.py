import os
import httpx
from fastapi import FastAPI, Request
from mcp.server.mcpserver import MCPServer
from mcp.server.sse import SseServerTransport

# 1. MCPServer の初期化
mcp = MCPServer("weather-mcp-server")

# 2. ツールの登録
@mcp.tool()
async def get_weather(latitude: float, longitude: float) -> str:
    """指定された緯度・経度の現在の天気を取得します。

    Args:
        latitude: 緯度（例: 東京は 35.6762）
        longitude: 経度（例: 東京は 139.6503）
    """
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    
    async with httpx.AsyncClient() as client:
        res = await client.get(url)
        data = res.json()

    if "current_weather" not in data:
        return "天気情報の取得に失敗しました。"

    cw = data["current_weather"]
    return f"気温: {cw['temperature']}°C, 風速: {cw['windspeed']}km/h"

# 3. FastAPI アプリの設定
app = FastAPI()

# GET /sse -> Dify からの初期接続を受け付ける
@app.get("/sse")
async def handle_sse(request: Request):
    # リクエストのヘッダー情報からスキーム（https）とホスト名を取得し、完全な絶対URLを構築
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    endpoint_url = f"{scheme}://{host}/messages"

    # 完全なURL（https://test20260831.onrender.com/messages）を指定してTransportを作成
    transport = SseServerTransport(endpoint_url)

    async with transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp._mcp_server.run(
            streams[0], streams[1], mcp._mcp_server.create_initialization_options()
        )

# POST /messages -> Dify からのツール実行命令を受け取る
@app.post("/messages")
async def handle_messages(request: Request):
    # POST処理用にもダミーのTransportを用意してメッセージを通過させる
    transport = SseServerTransport("/messages")
    await transport.handle_post_message(
        request.scope, request.receive, request._send
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
