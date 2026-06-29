import os
import re
from typing import Any
from urllib.parse import urljoin

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

    body_methods = {"POST", "PUT"}

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
        settings = get_settings()
        timeout_ms = int(
            skill.executor.get("timeout_ms")
            or settings.skill_api_timeout_ms
        )
        request_spec = self._build_request_spec(skill, api_payload, context)
        if request_spec.get("missing_params"):
            return self._missing_params_result(
                request_spec["missing_params"],
                "API Skill 缺少运行时上下文字段",
            )
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            response = await self._request(client, request_spec)
        return self._map_response(skill, response.json())

    def _build_request_spec(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """
        构建 HTTP 请求规格。
        """
        method = str(skill.executor.get("method") or "GET").upper()
        if method not in {"GET", "POST", "PUT", "DELETE"}:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"API Skill method 不支持: {method}"
            )
        url_result = self._build_url(skill, payload, context)
        missing_params = list(url_result.get("missing_params") or [])
        request_payload = {
            key: value
            for key, value in payload.items()
            if key not in set(url_result.get("consumed_params") or [])
        }
        query_params: dict[str, Any] = {}
        body_payload: dict[str, Any] = {}
        if method in self.body_methods:
            body_payload = dict(request_payload)
            body_missing = self._inject_body_context_fields(
                skill,
                body_payload,
                payload,
                context,
            )
            missing_params.extend(body_missing)
        else:
            query_params = dict(request_payload)
        self._apply_auth(skill, query_params)
        return {
            "method": method,
            "url": url_result.get("url", ""),
            "query_params": query_params,
            "body": body_payload,
            "missing_params": missing_params,
        }

    async def _request(
        self,
        client: httpx.AsyncClient,
        request_spec: dict[str, Any],
    ) -> httpx.Response:
        """
        发起 HTTP 请求。
        """
        method = str(request_spec.get("method") or "GET")
        url = str(request_spec.get("url") or "")
        if method == "GET":
            response = await client.get(url, params=request_spec.get("query_params") or {})
        elif method == "POST":
            response = await client.post(
                url,
                params=request_spec.get("query_params") or {},
                json=request_spec.get("body") or {},
            )
        elif method == "PUT":
            response = await client.put(
                url,
                params=request_spec.get("query_params") or {},
                json=request_spec.get("body") or {},
            )
        elif method == "DELETE":
            response = await client.delete(url, params=request_spec.get("query_params") or {})
        else:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"API Skill method 不支持: {method}"
            )
        response.raise_for_status()
        return response

    def _build_url(
        self,
        skill: SkillDefinition,
        payload: dict[str, Any],
        context: RuntimeContext,
    ) -> dict[str, Any]:
        """
        组装请求地址并替换路径模板参数。
        """
        endpoint = str(skill.executor.get("endpoint") or "")
        if not endpoint:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("API Skill 缺少 endpoint")
        base_url_env = str(skill.executor.get("base_url_env") or "")
        if not base_url_env:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception("API Skill 缺少 base_url_env")
        base_url = os.getenv(base_url_env, "")
        if not base_url:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                f"缺少环境变量: {base_url_env}"
            )
        url = urljoin(f"{base_url.rstrip('/')}/", endpoint.lstrip("/"))
        path_params = skill.executor.get("path_params") or {}
        missing_params: list[str] = []
        consumed_params: list[str] = []

        def replace(match: re.Match[str]) -> str:
            name = match.group(1)
            source = self._path_param_source(path_params, name)
            value = self._resolve_field(source, payload, context)
            if self._is_missing(value):
                missing_params.append(name)
                return match.group(0)
            consumed_name = self._consumed_payload_name(source, name)
            if consumed_name:
                consumed_params.append(consumed_name)
            return str(value)

        url = re.sub(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", replace, url)
        return {
            "url": url,
            "missing_params": sorted(set(missing_params)),
            "consumed_params": sorted(set(consumed_params)),
        }

    def _path_param_source(self, path_params: Any, name: str) -> str:
        """
        获取路径模板参数的数据来源。
        """
        if isinstance(path_params, dict):
            return str(path_params.get(name) or f"payload.{name}")
        if isinstance(path_params, list) and name in path_params:
            return f"payload.{name}"
        return f"payload.{name}"

    def _inject_body_context_fields(
        self,
        skill: SkillDefinition,
        body_payload: dict[str, Any],
        payload: dict[str, Any],
        context: RuntimeContext,
    ) -> list[str]:
        """
        从 Runtime context 注入字段到请求 body。
        """
        fields = skill.executor.get("body_context_fields") or {}
        missing_params: list[str] = []
        if isinstance(fields, dict):
            items = fields.items()
        elif isinstance(fields, list):
            items = [
                (self._field_name_from_source(str(source)), str(source))
                for source in fields
            ]
        else:
            raise BizErrorCode.ACTION_EXECUTE_ERROR.exception(
                "body_context_fields 必须是对象或数组"
            )
        for body_field, source in items:
            target_field = str(body_field)
            source_path = str(source)
            value = self._resolve_field(source_path, payload, context)
            if self._is_missing(value):
                missing_params.append(target_field)
                continue
            body_payload[target_field] = value
        return sorted(set(missing_params))

    def _field_name_from_source(self, source: str) -> str:
        """
        从 source path 推导 body 字段名。
        """
        return source.split(".")[-1] if source else source

    def _resolve_field(
        self,
        source: str,
        payload: dict[str, Any],
        context: RuntimeContext,
    ) -> Any:
        """
        从 payload 或 Runtime context 读取字段。
        """
        source = source.strip()
        if not source:
            return None
        if "." not in source:
            value = payload.get(source)
            if not self._is_missing(value):
                return value
            value = context.request.metadata.get(source)
            if not self._is_missing(value):
                return value
            return context.session_context.get(source)
        root, _, path = source.partition(".")
        roots = {
            "payload": payload,
            "metadata": context.request.metadata,
            "request": {
                "user_id": context.request.user_id,
                "agent_id": context.request.agent_id,
                "session_id": context.request.session_id,
                "request_id": context.request.request_id,
                "metadata": context.request.metadata,
            },
            "session_context": context.session_context,
            "previous_action_result": (
                context.previous_action_result.to_dict()
                if context.previous_action_result
                else {}
            ),
        }
        return self._dig(roots.get(root, {}), path)

    def _dig(self, value: Any, path: str) -> Any:
        """
        按点路径读取嵌套字段。
        """
        current = value
        for part in [item for item in path.split(".") if item]:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                current = getattr(current, part, None)
            if current is None:
                return None
        return current

    def _consumed_payload_name(self, source: str, name: str) -> str:
        """
        获取需要从 payload 中消费的路径参数字段。
        """
        if source == name:
            return name
        prefix = "payload."
        if source.startswith(prefix):
            payload_path = source[len(prefix):]
            return payload_path.split(".", 1)[0]
        return ""

    def _is_missing(self, value: Any) -> bool:
        """
        判断运行时字段是否缺失。
        """
        return value is None or value == ""

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
        if kind == "amap_route_driving":
            return self._map_amap_route_driving(response)
        if kind == "amap_generic":
            return self._map_amap_generic(response)
        if kind == "backend_envelope":
            return self._map_backend_envelope(skill, response)
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

    def _map_amap_generic(self, response: dict[str, Any]) -> dict[str, Any]:
        """
        映射高德通用接口响应。
        """
        failed = self._amap_failed(response)
        if failed:
            return failed
        return self._success(
            {"raw": response},
            str(response.get("info") or "高德接口调用完成"),
        )

    def _map_backend_envelope(
        self,
        skill: SkillDefinition,
        response: dict[str, Any],
    ) -> dict[str, Any]:
        """
        映射后端 BaseResponse 响应。
        """
        mapping = skill.executor.get("response_mapping") or {}
        code_field = str(mapping.get("code_field") or "code")
        msg_field = str(mapping.get("msg_field") or "msg")
        data_field = str(mapping.get("data_field") or "data")
        code = response.get(code_field)
        success_codes = mapping.get("success_codes")
        if success_codes is None:
            success_codes = [mapping.get("success_code", 200)]
        elif not isinstance(success_codes, list):
            success_codes = [success_codes]
        normalized_codes = {str(item) for item in success_codes}
        message = str(response.get(msg_field) or "")
        data = response.get(data_field)
        if str(code) not in normalized_codes:
            error = message or "后端接口返回失败"
            return {
                "status": "failed",
                "data": {"raw": response},
                "summary": error,
                "missing_params": [],
                "error": error,
            }
        return self._success(
            data if isinstance(data, dict) else {"value": data},
            message or "后端接口调用完成",
        )

    def _map_amap_route_driving(self, response: dict[str, Any]) -> dict[str, Any]:
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

    def _missing_params_result(
        self,
        missing_params: list[str],
        summary: str,
    ) -> dict[str, Any]:
        """
        构造缺参结果。
        """
        return {
            "status": "missing_params",
            "data": {},
            "summary": summary,
            "missing_params": missing_params,
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
            "amap_route_driving",
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
                    {"skill_id": "amap_route_driving", "summary": route.summary},
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
