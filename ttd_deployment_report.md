# MixMaster AI 正式版部署记录

## 当前服务

- 内网入口：`http://ttd-stage:17862/`（沿用原地址）
- 主机与目录：`ttd-stage:/opt/mixmaster-ai`
- Compose：`docker-compose.yml`
- 容器：`mixmaster-ai`
- 镜像：`registry.ttd/mixmaster-ai/mixmaster-ai:h-615c4fa22440`
- 镜像 digest：`sha256:b967e6595d489a2c34bf5c716729f713001f38a9b12481f26a28a5f2e5e919c4`
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
ssh ttd-stage 'cd /opt/mixmaster-ai && MIXMASTER_IMAGE=registry.ttd/mixmaster-ai/mixmaster-ai:h-615c4fa22440 docker compose up -d --no-build'
```

原预览版 Compose 和 `mixmaster-ai:preview` 镜像保留作回退参考，不再作为日常启动入口。正式部署配置位于本仓库的 `docker-compose.yml` 与 `Dockerfile`；模型及代理配置由主机私有 `.env` 提供。

## 2026-09-28 伴奏区域折叠发布

- `伴奏（可选）` 改为 Gradio Accordion，默认关闭；上传与处理函数绑定保持原样。
- 正式仓库：`FC-TTD/mixmaster-ai`，分支 `ttd`；本次运行源码提交：`faf39a4`。
- 从该提交的只读 `git archive` 构建；归档 SHA-256：`615c4fa2244044a0ec8566b2bcaaaa91afc51000ad557c8e3fa70f489ab28e34`。构建前后归档哈希一致。
- 基础镜像固定 digest；第二次同输入构建的所有应用层均命中缓存，镜像 digest 保持 `sha256:b967e6595d489a2c34bf5c716729f713001f38a9b12481f26a28a5f2e5e919c4`。
- 共享 `docker_ci_cd` 角色在连接 `ttd-nest` 管理目录时缺少 SSH 写权限；本次从只读快照通过 `hub-immutable-builder` 直连同一台 `ttd-nest` BuildKit 构建，项目 `deploy.sh build` 固化了该路径。未发布可变镜像标签。
- 预验收：候选镜像导入 `api.py` 成功，Gradio 6.22.0 配置显示 `open=false`；本地回环端口上的 `/master` 返回 HTTP 200，输出双声道、22.05 kHz、24-bit WAV。
- 正式验收：`http://ttd-stage:17862/config` 显示伴奏 Accordion 默认关闭；正式 `/master` 返回 HTTP 200 和同规格有效 WAV；容器健康为 `healthy`。部署过程未修改私有 `.env` 或模型路由。
- 回退镜像：`mixmaster-ai:1.0.0-ttd`，原镜像 ID 为 `sha256:39b5ef7fca6fb95f2167c90a4129181d513f4772666853732275d21fef0c21d8`；部署前 Compose 备份于主机 `/opt/mixmaster-ai/docker-compose.rollback.yml`。回退时恢复该 Compose 文件并执行 `docker compose up -d --no-build`，保留原 `mixmaster_ai_tmp` 卷。
- 当前入口继续使用原直接端口 `17862`，未更改已有网络入口或接入新的内部 Caddy 路由。
