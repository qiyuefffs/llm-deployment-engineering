---
id: EV04
title: "性能指标口径"
type: evidence
volume: evidence
layer: 4
platform: "general"
device: "general"
status: historical
source_ids: []
updated: 2026-10-19
summary: "统一 TTFT、TPOT、Decode、Prefill、输出吞吐和内存指标的测量边界。"
---

# 性能指标口径

| 指标 | 定义 | 必须补充的边界 |
| --- | --- | --- |
| TTFT | 请求发出到首个有效正文 token | 是否包含排队、网络、tokenizer 和首 token 采样 |
| TPOT / ITL | 首 token 后每 token 时间 / 相邻 token 间隔 | 是否包含首 token，按实际输出 token 还是请求参数计算 |
| Decode tok/s | 首 token 后输出 token / 持续时间 | 引擎 eval 还是 HTTP 墙钟，是否包含采样和流式写回 |
| Prefill tok/s | 输入 token / prefill 时间 | 是否包含 tokenizer、模板、图像编码和缓存命中 |
| 输出吞吐 | 成功请求输出 token 总数 / 测试窗口 | 并发、到达率、请求数、实际输出 token 和失败请求处理 |
| 接受率 | accepted / drafted | 草稿来源、候选数、温度、验证策略和是否含 bonus token |
| 显存 / 内存 | VRAM、GTT/TTM、RSS、峰值工作区 | 采样工具、采样窗口、是否包含模型加载和共享内存 |

## 记录规则

1. 每个性能数字必须带单位。
2. 引擎内部速度与服务端吞吐分开命名。
3. 同一张表只比较相同负载和相同统计方式；不同负载不得按绝对值交叉排名。
4. 平均延迟不能替代尾延迟；单请求不能证明并发能力。
5. 性能通过不等于功能或质量通过，三者分别验收。

