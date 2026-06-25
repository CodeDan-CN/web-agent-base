# amap_direction_driving

## 用途

调用高德 Web 服务驾车路径规划接口，根据起点和终点经纬度查询驾车路线。

## 适用场景

- 用户提供了起点和终点经纬度。
- 链路 Skill 已通过地理编码得到起终点经纬度。
- 用户询问驾车路线、距离或预计耗时。

## 不适用场景

- 用户只提供自然语言地址且上下文无法补齐经纬度。

## 调用注意事项

- 必须提供 `origin` 和 `destination`，格式为 `lng,lat`。
- `extensions` 可选，默认 `base`。
- API Key 由 Runtime 从 `.env` 读取。
