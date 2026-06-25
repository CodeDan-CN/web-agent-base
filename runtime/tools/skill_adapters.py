import os
from typing import Any

import httpx

from exception.error_code import BizErrorCode
from runtime.context.assembler import RuntimeContext
from runtime.models import ActionResult
from runtime.tools.builtin_skills import CODE_SKILL_EXECUTORS
from runtime.tools.skill_definition import SkillDefinition
from runtime.tools.skill_registry import SkillRegistry
from utils.config import get_settings


class BaseSkillAdapter:
    """
    Skill Adapter 基类。
    """

    async def execute(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
        executor: Any,
        depth: int,
    ) -> dict[str, Any]:
        """
        执行 Skill。
        """
        raise NotImplementedError


class CodeSkillAdapter(BaseSkillAdapter):
    """
    本地代码 Skill Adapter。
    """

    async def execute(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
        executor: Any,
        depth: int,
    ) -> dict[str, Any]:
        """
        执行 builtin code skill。
        """
        executor_name = str(skill.executor.get("name") or skill.skill_id)
        skill_cls = CODE_SKILL_EXECUTORS.get(executor_name)
        if not skill_cls:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"未找到 Code Skill: {executor_name}"
            )
        return await skill_cls().run(payload, context)


class ApiSkillAdapter(BaseSkillAdapter):
    """
    HTTP API Skill Adapter。
    """

    async def execute(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
        executor: Any,
        depth: int,
    ) -> dict[str, Any]:
        """
        执行 HTTP API Skill。
        """
        api_payload = dict(payload)
        self._apply_auth(skill, api_payload)
        timeout_ms = int(
            skill.executor.get("timeout_ms")
            or get_settings().skill_api_timeout_ms
        )
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            response = await self._request(client, skill, api_payload)
        return self._map_response(skill, response.json())

    async def _request(
        self,
        client: httpx.AsyncClient,
        skill: SkillDefinition,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """
        发起 HTTP 请求。
        """
        method = str(skill.executor.get("method") or "GET").upper()
        endpoint = str(skill.executor.get("endpoint") or "")
        if not endpoint:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("API Skill 缺少 endpoint")
        if method == "GET":
            response = await client.get(endpoint, params=payload)
        elif method == "POST":
            response = await client.post(endpoint, json=payload)
        else:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"API Skill method 不支持: {method}"
            )
        response.raise_for_status()
        return response

    def _apply_auth(self, skill: SkillDefinition, payload: dict[str, Any]) -> None:
        """
        注入 API 鉴权参数。
        """
        auth = skill.executor.get("auth") or {}
        if auth.get("type") != "query":
            return
        env_name = str(auth.get("env") or "")
        param_name = str(auth.get("param") or "")
        if not env_name or not param_name:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("API auth 配置不完整")
        key = os.getenv(env_name, "")
        if not key:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(f"缺少环境变量: {env_name}")
        payload[param_name] = key

    def _map_response(self, skill: SkillDefinition, response: dict[str, Any]) -> dict[str, Any]:
        """
        将 API 响应映射为统一 SkillResult。
        """
        kind = (skill.executor.get("response_mapping") or {}).get("kind")
        if kind == "amap_geocode":
            return self._map_amap_geocode(response)
        if kind == "amap_weather":
            return self._map_amap_weather(response)
        if kind == "amap_direction_driving":
            return self._map_amap_direction_driving(response)
        return {
            "status": "success",
            "data": response,
            "summary": "API Skill 调用完成",
            "missing_params": [],
            "error": None,
        }

    def _amap_failed(self, response: dict[str, Any]) -> dict[str, Any] | None:
        """
        检查高德接口失败响应。
        """
        if str(response.get("status")) == "1":
            return None
        error = str(response.get("info") or "高德接口调用失败")
        return {
            "status": "failed",
            "data": {"raw": response},
            "summary": error,
            "missing_params": [],
            "error": error,
        }

    def _map_amap_geocode(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        映射高德地理编码响应。
        """
        failed = self._amap_failed(response)
        if failed:
            return failed
        geocodes = response.get("geocodes") or []
        if not geocodes:
            return {
                "status": "partial_success",
                "data": {"raw": response},
                "summary": "未解析到地址坐标",
                "missing_params": [],
                "error": None,
            }
        item = geocodes[0]
        data = {
            "formatted_address": item.get("formatted_address"),
            "location": item.get("location"),
            "adcode": item.get("adcode"),
            "citycode": item.get("citycode"),
            "city": item.get("city"),
            "province": item.get("province"),
            "district": item.get("district"),
        }
        return {
            "status": "success",
            "data": data,
            "summary": f"已解析地址: {data.get('formatted_address')}",
            "missing_params": [],
            "error": None,
        }

    def _map_amap_weather(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        映射高德天气响应。
        """
        failed = self._amap_failed(response)
        if failed:
            return failed
        lives = response.get("lives") or []
        forecasts = response.get("forecasts") or []
        if lives:
            item = lives[0]
            data = {
                "province": item.get("province"),
                "city": item.get("city"),
                "adcode": item.get("adcode"),
                "weather": item.get("weather"),
                "temperature": item.get("temperature"),
                "wind_direction": item.get("winddirection"),
                "wind_power": item.get("windpower"),
                "humidity": item.get("humidity"),
                "report_time": item.get("reporttime"),
            }
            summary = f"{data.get('city')} 当前天气 {data.get('weather')}，{data.get('temperature')}℃"
            return self._success(data, summary)
        if forecasts:
            item = forecasts[0]
            data = {
                "province": item.get("province"),
                "city": item.get("city"),
                "adcode": item.get("adcode"),
                "report_time": item.get("reporttime"),
                "casts": item.get("casts") or [],
            }
            return self._success(data, f"已查询 {data.get('city')} 天气预报")
        return {
            "status": "partial_success",
            "data": {"raw": response},
            "summary": "未查询到天气数据",
            "missing_params": [],
            "error": None,
        }

    def _map_amap_direction_driving(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        映射高德驾车路径规划响应。
        """
        failed = self._amap_failed(response)
        if failed:
            return failed
        route = response.get("route") or {}
        paths = route.get("paths") or []
        if not paths:
            return {
                "status": "partial_success",
                "data": {"raw": response},
                "summary": "未查询到可用路线",
                "missing_params": [],
                "error": None,
            }
        path = paths[0]
        distance = int(path.get("distance") or 0)
        duration = int(path.get("duration") or 0)
        data = {
            "origin": route.get("origin"),
            "destination": route.get("destination"),
            "distance_meters": distance,
            "duration_seconds": duration,
            "route_summary": self._route_summary(distance, duration),
            "strategy": path.get("strategy"),
            "steps": self._route_steps(path),
        }
        return self._success(data, data["route_summary"])

    def _route_summary(self, distance: int, duration: int) -> str:
        """
        构造路线摘要。
        """
        distance_km = round(distance / 1000, 1) if distance else 0
        minutes = round(duration / 60) if duration else 0
        return f"驾车约 {distance_km} 公里，预计 {minutes} 分钟"

    def _route_steps(self, path: dict[str, Any]) -> list[dict[str, Any]]:
        """
        提取路线步骤。
        """
        steps = path.get("steps") or []
        return [
            {
                "instruction": item.get("instruction"),
                "road": item.get("road"),
                "distance": item.get("distance"),
                "duration": item.get("duration"),
            }
            for item in steps[:8]
        ]

    def _success(self, data: dict[str, Any], summary: str) -> dict[str, Any]:
        """
        构造成功结果。
        """
        return {
            "status": "success",
            "data": data,
            "summary": summary,
            "missing_params": [],
            "error": None,
        }


class ChainSkillAdapter(BaseSkillAdapter):
    """
    固定链路 Skill Adapter。
    """

    async def execute(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
        executor: Any,
        depth: int,
    ) -> dict[str, Any]:
        """
        执行固定链路 Skill。
        """
        chain_id = str(skill.executor.get("chain_id") or "")
        if chain_id != "amap_route_weather_plan":
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(f"未知 Chain Skill: {chain_id}")
        return await self._run_amap_route_weather_plan(payload, context, executor, depth)

    async def _run_amap_route_weather_plan(
        self,
        payload: dict[str, Any],
        context: RuntimeContext,
        executor: Any,
        depth: int,
    ) -> dict[str, Any]:
        """
        执行路线天气固定链路。
        """
        origin_address = str(payload.get("origin_address") or "")
        destination_address = str(payload.get("destination_address") or "")
        city = str(payload.get("city") or "")
        origin = await executor.execute_by_skill_id(
            "amap_geocode",
            {"address": origin_address, **({"city": city} if city else {})},
            context,
            depth + 1,
        )
        if origin.status != "success":
            return self._chain_failed("起点地址解析失败", origin)
        destination = await executor.execute_by_skill_id(
            "amap_geocode",
            {"address": destination_address, **({"city": city} if city else {})},
            context,
            depth + 1,
        )
        if destination.status != "success":
            return self._chain_failed("终点地址解析失败", destination)
        route = await executor.execute_by_skill_id(
            "amap_direction_driving",
            {
                "origin": str(origin.data.get("location") or ""),
                "destination": str(destination.data.get("location") or ""),
                "extensions": str(payload.get("route_extensions") or "base"),
            },
            context,
            depth + 1,
        )
        if route.status != "success":
            return self._chain_failed("路径规划失败", route)
        weather = await executor.execute_by_skill_id(
            "amap_weather",
            {
                "city": str(destination.data.get("adcode") or ""),
                "extensions": str(payload.get("weather_extensions") or "base"),
            },
            context,
            depth + 1,
        )
        if weather.status != "success":
            return self._chain_failed("天气查询失败", weather)
        briefing = await executor.execute_by_skill_id(
            "travel_briefing_formatter",
            {
                "origin_address": origin_address,
                "destination_address": destination_address,
                "route": route.data,
                "weather": weather.data,
            },
            context,
            depth + 1,
        )
        return {
            "status": briefing.status,
            "data": {
                "origin": origin.data,
                "destination": destination.data,
                "route": route.data,
                "weather": weather.data,
                "briefing": briefing.data,
                "steps": [
                    {"skill_id": "amap_geocode", "summary": origin.summary},
                    {"skill_id": "amap_geocode", "summary": destination.summary},
                    {"skill_id": "amap_direction_driving", "summary": route.summary},
                    {"skill_id": "amap_weather", "summary": weather.summary},
                    {"skill_id": "travel_briefing_formatter", "summary": briefing.summary},
                ],
            },
            "summary": briefing.summary or "路线天气链路执行完成",
            "missing_params": briefing.missing_params,
            "error": briefing.error,
        }

    def _chain_failed(self, summary: str, result: ActionResult) -> dict[str, Any]:
        """
        构造链路失败结果。
        """
        return {
            "status": result.status if result.status != "success" else "failed",
            "data": {"failed_step": result.to_dict()},
            "summary": summary,
            "missing_params": result.missing_params,
            "error": result.error or summary,
        }


def build_skill_adapters(registry: SkillRegistry) -> dict[str, BaseSkillAdapter]:
    """
    构造 Skill Adapter 映射。
    """
    return {
        "api": ApiSkillAdapter(),
        "chain": ChainSkillAdapter(),
        "code": CodeSkillAdapter(),
    }
