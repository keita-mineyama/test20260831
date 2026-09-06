import os
import httpx
from mcp.server.mcpserver import MCPServer

# 1. MCPServer（mcp 2.x最新版）の初期化
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    # SSEモードでサーバー起動（自動的に /sse エンドポイントが作られます）
    mcp.run(transport="sse", host="0.0.0.0", port=port)