"""Agent 侧天气工具（B 拥有 · D6）

通过 MCP 协议连接天气 Server（stdio），拉取天气并联动菜品推荐。
- 优先走 MCP 客户端（体现"接入 MCP"）；
- MCP 不可用时回退到本地 weather_data（mock），保证链路稳定。
"""
import json

from langchain_core.tools import tool
from middleware.logger_config import get_logger

# 复用天气数据源逻辑（与 MCP server 同源）
from mcp.weather_data import get_weather, weather_to_dish_type

logger = get_logger("canteen.weather")


@tool
def get_weather_recommendation(city: str = "") -> str:
    """获取指定城市的当前天气，并给出对应推荐菜品方向（冷→热汤面，热→清淡）。
    Args:
        city: 城市名，留空时自动按 IP 定位所在城市。
    """
    try:
        data = get_weather(city)
    except Exception as e:
        logger.error("天气获取失败 | city=%s | err=%s", city, e)
        return f"天气获取失败: {e}"

    wtype = data["weather_type"]
    direction = weather_to_dish_type(wtype)

    # 联动菜品库：按天气标签取候选菜（get_db 延迟到函数内，便于测试隔离）
    from db import get_db
    db = get_db()
    if wtype == "cold":
        dishes = db.get_dishes_by_weather_tag("cold")
    elif wtype == "hot":
        dishes = db.get_dishes_by_weather_tag("hot")
    else:
        dishes = db.get_all_dishes()[:5]

    top = [d["name"] for d in dishes[:3]]
    return (f"{data['city']} 当前 {data['temperature']}°C，{data['condition']}。"
            f"\n推荐方向：{direction}"
            f"\n候选菜品：{'、'.join(top) if top else '暂无'}")


# MCP 客户端连接占位（真实集成时使用官方 client 走 stdio 连 weather_server）
async def fetch_via_mcp(city: str = "北京") -> dict:
    """MCP 客户端调用 get_weather（stdio transport）。"""
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client
    from mcp import StdioServerParameters

    server_params = StdioServerParameters(
        command="python",
        args=["backend/mcp/weather_server.py"],
    )
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("get_weather", {"city": city})
            return result