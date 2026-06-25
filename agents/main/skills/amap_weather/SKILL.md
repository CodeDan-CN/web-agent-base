# amap_weather

## 用途

调用高德 Web 服务天气查询接口，根据 adcode 查询实时天气或天气预报。

## 适用场景

- 用户提供了城市 adcode。
- 链路 Skill 已通过地理编码获得目的地 adcode。
- 用户询问某个区域实时天气或天气预报。

## 不适用场景

- 用户只提供地址但没有 adcode，且上下文无法补齐。

## 调用注意事项

- 必须提供 `city`，其值为 adcode。
- `extensions=base` 查询实时天气。
- `extensions=all` 查询天气预报。
- API Key 由 Runtime 从 `.env` 读取。
