# MixMaster AI 正式版部署记录

## 当前服务

- 内网入口：`http://ttd-stage:17862/`（沿用原地址）
- 主机与目录：`ttd-stage:/opt/mixmaster-ai`
- Compose：`docker-compose.yml`
- 容器：`mixmaster-ai`
- 镜像：`mixmaster-ai:1.0.0-ttd`
- 大模型：`gpt-6-luna`，通过 `http://aiproxy/v1` 调用
- CPU 运行；保留原 `mixmaster-ai_mixmaster_ai_tmp` 卷与 `17862:7860` 端口映射。

## 2026-09-27 发布与验收

- 将已验证的 GPT-6 Luna 母带决策提示词发布为正式部署；Gradio 页面、API 路径和混音规则未改。
- 构建时排除 `.env`、备份文件和缓存；镜像检查未发现私密环境文件。
- 正式容器健康状态为 `healthy`，运行环境读取 `OPENAI_MODEL=gpt-6-luna`。
- `POST /master` 与 `POST /mix-and-master` 均以合成测试音频返回 HTTP 200，结果为 24-bit、22.05 kHz、双声道 WAV。
- 原页面 `GET /` 返回 HTTP 200。
- 正式镜像运行项目测试：`67 passed`。旧代理测试通过 fixture 固定为其模拟的 Anthropic 路径，避免测试环境默认的 GPT-6 Luna 配置触发真实调用。

## 日常运维

```bash
ssh ttd-stage 'cd /opt/mixmaster-ai && docker compose ps'
ssh ttd-stage 'docker logs --tail 100 mixmaster-ai'
ssh ttd-stage 'cd /opt/mixmaster-ai && docker compose up -d --no-build'
```

原预览版 Compose 和 `mixmaster-ai:preview` 镜像保留作回退参考，不再作为日常启动入口。正式部署配置位于本仓库的 `docker-compose.yml` 与 `Dockerfile`；模型及代理配置由主机私有 `.env` 提供。
