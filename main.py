import os
import httpx
from fastapi import FastAPI, Request
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent

mcp_server = Server("weather-mcp-server")

@mcp_server.list_tools()
async def list_tools():
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

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_weather":
        lat = arguments.get("latitude")
        lon = arguments.get("longitude")
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        
        async with httpx.AsyncClient() as client:
            res = await client.get(url)
            data = res.json()

        if "current_weather" not in data:
            return [TextContent(type="text", text="失敗しました")]

        cw = data["current_weather"]
        return [TextContent(type="text", text=f"気温: {cw['temperature']}°C, 風速: {cw['windspeed']}km/h")]

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
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))