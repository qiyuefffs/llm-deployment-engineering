# llama.cpp 部署性能优化 Case

从 [新手教程](CASE.md) 开始；[技术附录](CASE_TECHNICAL.md)说明指标口径和实验限制。

## 目录用途

| 路径 | 用途 | 公开上传 |
| --- | --- | --- |
| `CASE.md`、`CASE_TECHNICAL.md` | 正文和方法细节 | 是 |
| `scripts/` | 下载、部署、功能检查、压测和报告代码 | 是，排除 `__pycache__` |
| `data/workload.jsonl` | 可公开的测试输入 | 是 |
| `figures/` | 已有的真实核验截图 | 是，上传前再次检查敏感信息 |
| `results/observed-summary.csv` | 从本次运行结果转录的 12 组汇总 | 是，注明不是原始请求记录 |
| `local-cache/` | 本地源码包、早期打包文件、Python 缓存 | 否 |
| `models/`、`cuda12/`、`build-cuda12/`、`logs/` | Notebook 运行时生成 | 否 |

当前材料是教程草稿。成功编译的完整日志、全新实例从头复现记录，以及可公开访问的逐请求原始结果还未齐备，不能标记为可正式投稿的完整 Case。

## 上传位置

1. **公开代码仓库**：本文发布在 [qiyuefffs/llm-serving-diagnosis](https://github.com/qiyuefffs/llm-serving-diagnosis)。仓库只包含教程、代码、样例数据、截图和转录汇总；不要把整个个人项目仓库或 `local-cache/` 一起公开。
2. **魔搭 Notebook**：在 GPU 实例的 `/mnt/workspace/` 运行 `git clone https://github.com/qiyuefffs/llm-serving-diagnosis.git`，之后按 `CASE.md` 从第一步执行。Notebook 工作区主要用于运行和保存真实输出；临时实例路径不是公开分享链接。
3. **正式投稿前**：在全新实例跑通并保存构建日志、原始 JSONL、GPU 采样和报告。检查日志与截图中的账号、路径和其他敏感信息后，放到公开仓库的 `evidence/` 或可长期访问的公开存储，并在正文加入链接。若魔搭提供可公开访问的 Notebook 文件页面，再同时给出该页面链接。
4. **魔搭 Cookbook/创空间**：最终文章引用公开仓库和可访问的运行证据。创空间仅在需要交互演示时建立；这个性能对照 Case 的核心交付物是可复跑脚本、日志和报告，不必为展示而常驻运行 27B 模型服务。

仓库不包含 16.8GB 模型权重或 37MB 的源码压缩包。模型和源码由 `scripts/setup.sh` 按固定地址下载并校验 SHA256。
