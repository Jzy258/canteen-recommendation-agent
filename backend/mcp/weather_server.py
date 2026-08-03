"""天气 MCP Server（B 拥有 · D6）

独立进程，通过 MCP 协议暴露 `get_weather` 工具。
以脚本方式启动（推荐，避免本地 mcp 包遮蔽 SDK）：
    uv run python backend/mcp/weather_server.py

说明：本机 `backend/mcp/` 目录与 MCP SDK 同名，为避免 `backend/` 进入
sys.path 时遮蔽 SDK，weather_data 通过 importlib 按文件路径加载。
"""
import asyncio
import importlib.util
import os
import sys

from mcp import types
from mcp.server import Server
from mcp.server.runner import serve_connection
from mcp.server.stdio import stdio_server


def _load_weather_data():
    """按文件路径加载 weather_data 模块，规避包同名遮蔽。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "weather_data.py")
    spec = importlib.util.spec_from_file_location("weather_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_data = _load_weather_data()
get_weather = _data.get_weather
weather_to_dish_type = _data.weather_to_dish_type


def _load_version():
    """按文件路径加载 version 模块（规避包同名遮蔽），返回版本号。"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "version.py")
    spec = importlib.util.spec_from_file_location("canteen_version", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.VERSION


server = Server(
    "canteen-weather",
    version=_load_version(),
    title="Canteen Weather MCP",
    description="食堂天气 MCP：提供城市温度与天气类型，辅助按天气推荐菜品。",
)


async def _list_tools(ctx, params=None) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[
        types.Tool(
            name="get_weather",
            description="获取城市当前温度与天气类型（cold/hot/mild），"
                        "并给出对应推荐菜品方向。",
            inputSchema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，默认北京"},
                },
                "required": [],
            },
        ),
    ])


async def _call_tool(ctx, params: types.CallToolRequestParams) -> types.CallToolResult:
    if params.name == "get_weather":
        args = params.arguments or {}
        city = str(args.get("city", "北京"))
        try:
            data = get_weather(city)
            text = (f"{data['city']} 当前 {data['temperature']}°C，"
                    f"{data['condition']}（{data['weather_type']}）。"
                    f"建议：{weather_to_dish_type(data['weather_type'])}")
            return types.CallToolResult(content=[{"type": "text", "text": text}])
        except Exception as e:
            return types.CallToolResult(isError=True,
                                        content=[{"type": "text", "text": f"天气获取失败: {e}"}])
    return types.CallToolResult(isError=True, content=[{"type": "text", "text": "未知工具"}])


server.on_list_tools = _list_tools
server.on_call_tool = _call_tool


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await serve_connection(
            server, read_stream, write_stream,
            initialization_options=server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())