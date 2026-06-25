from typing import Any

from runtime.tools.builtin_skills.base import BaseCodeSkill


class TravelBriefingFormatterSkill(BaseCodeSkill):
    """
    出行建议格式化 Code Skill。
    """

    name = "travel_briefing_formatter"

    async def run(self, payload: dict[str, Any], context: Any) -> dict[str, Any]:
        """
        生成出行建议。
        """
        origin = str(payload.get("origin_address") or "")
        destination = str(payload.get("destination_address") or "")
        route = payload.get("route") or {}
        weather = payload.get("weather") or {}
        suggestions = self._suggestions(route, weather)
        data = {
            "briefing": (
                f"从 {origin} 到 {destination}，{route.get('route_summary', '已获取路线')}。"
                f"目的地天气：{weather.get('weather', '未知')}。"
            ),
            "route": route,
            "weather": weather,
            "suggestions": suggestions,
        }
        return {
            "status": "success",
            "data": data,
            "summary": "已生成出行建议",
            "missing_params": [],
            "error": None,
        }

    def _suggestions(self, route: dict[str, Any], weather: dict[str, Any]) -> list[str]:
        """
        生成建议列表。
        """
        suggestions = ["出发前确认实时路况，预留一定机动时间。"]
        weather_text = str(weather.get("weather") or "")
        if any(keyword in weather_text for keyword in ["雨", "雪", "雷"]):
            suggestions.append("天气可能影响驾驶，请携带雨具并降低车速。")
        duration = int(route.get("duration_seconds") or 0)
        if duration >= 3600:
            suggestions.append("预计路程较长，建议提前规划休息点。")
        return suggestions
