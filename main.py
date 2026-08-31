import os
import httpx
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, CallToolRequestSchema, ListToolsRequestSchema

# 1. MCPサーバーの初期化
mcp_server = Server("weather-mcp-server")

# 2. 利用可能なツールの定義（最新SDK対応の書き方）
@mcp_server.list_tools()
async def handle_list_tools():
    return [
        Tool(
            name="get_weather",
            description="指定された緯度・経度の現在の天気を取得します",
            inputSchema={
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "緯度"},
                    "longitude": {"type": "number", "description": "経度"}
                },
                "required": ["latitude", "longitude"]
            }
        )
    ]

# もし上記でダメな場合（Low-level APIの互換性対策）
# 以下のハンドラー形式で登録します
async def list_tools_handler(request):
    return {
        "tools": [
            {
                "name": "get_weather",
                "description": "指定された緯度・経度の現在の天気を取得します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "latitude": {"type": "number", "description": "緯度"},
                        "longitude": {"type": "number", "description": "経度"}
                    },
                    "required": ["latitude", "longitude"]
                }
            }
        ]
    }

async def call_tool_handler(request):
    name = request.params.name
    arguments = request.params.arguments or {}
    
    if name == "get_weather":
        lat = arguments.get("latitude")
        lon = arguments.get("longitude")
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            data = res.json()

        if "current_weather" not in data:
            return {"content": [{"type": "text", "text": "失敗しました"}]}

        cw = data["current_weather"]
        return {
            "content": [
                {"type": "text", "text": f"気温: {cw['temperature']}°C, 風速: {cw['windspeed']}km/h"}
            ]
        }

    raise ValueError(f"Unknown tool: {name}")

# ハンドラーの設定
mcp_server.set_request_handler(ListToolsRequestSchema, list_tools_handler)
mcp_server.set_request_handler(CallToolRequestSchema, call_tool_handler)

# FastAPIアプリの設定
app = FastAPI()
sse = SseServerTransport("/messages")

@app.get("/sse")
async def handle_sse(request: Request):
    async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
        await mcp_server.run(streams[0], streams[1], mcp_server.create_initialization_options())

@app.post("/messages")
async def handle_messages(request: Request):
    await sse.handle_post_message(request.scope, request.receive, request._send)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)