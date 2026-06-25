# amap_regeocode

## 用途

调用高德逆地理编码接口，将经纬度转换为结构化地址信息。

## 适用场景

- 用户提供了经纬度，希望查询具体地址。
- 其他 Skill 得到坐标后，需要补充地址描述。

## 不适用场景

- 用户只提供自然语言地址，应该先使用 `amap_geocode`。

## 调用注意事项

- `location` 必须为 `lng,lat` 格式。
- API Key 由 Runtime 从 `.env` 读取。
