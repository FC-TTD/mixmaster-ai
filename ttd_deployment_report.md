# MixMaster AI 正式版部署记录

## 当前服务

- 内网入口：`http://ttd-stage:17862/`（沿用原地址）
- 主机与目录：`ttd-stage:/opt/mixmaster-ai`
- Compose：`docker-compose.yml`
- 容器：`mixmaster-ai`
- 镜像：`registry.ttd/mixmaster-ai/mixmaster-ai:h-0c6f8f349e96`
- 镜像 digest：`sha256:c2b1d37836744d64199a84da90d1bf8d5ffc81c05bc2686b61efb272c7e246e6`
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

## 2026-09-29 Luna 平台归属修复发布

- 正式 Compose 服务继续运行在 `root@ttd-stage:/opt/mixmaster-ai`，原入口 `http://ttd-stage:17862/`，无端口、卷或私有 `.env` 变更。变更的业务入口是单音频 `/master` 及同一母带处理路径的 Gradio 界面；模型对自然语言平台做分类，在一次响应中选用一套有来源的响度、真峰值参考及 DSP 参数。客户明确数值逐项覆盖预设。
- 源码提交 `43f293c8d65e095b7ec374fc81f50a6109dda088`；只读 `git archive` SHA-256 为 `0c6f8f349e962f06772a85ae8265e8e0f90846c1e333c14aef57471431210494`，构建前后相同。Dockerfile、Compose、部署脚本的 SHA-256 分别为 `82941e258f370693128164504a542effd0289a24341434fb5908f3abfbf42bfb`、`1017b4f7c349cf3070ddab1f29afaf86e549a3a2374eacf53319067b9055daab`、`e4fd8b9bc41f77b3986a2b5b7b90c292c5dcb473e760a91e29abe297cd5b1fd7`。
- 构建机 `ttd-nest` 的 root SSH 被拒；备用构建在 `ttd-stage` 的 Docker BuildKit 上从上述 tar 归档输入完成。独立 BuildKit 容器首次拉取受 Docker Hub 网络超时阻挡，遂使用已运行的默认 BuildKit。初次构建系统层命中缓存，Python 依赖层重新构建；同输入重复构建时全部应用层命中缓存，镜像摘要仍为 `sha256:c2b1d37836744d64199a84da90d1bf8d5ffc81c05bc2686b61efb272c7e246e6`。仅发布不可变 `h-*` 镜像；正式镜像内运行 `128 passed`。
- 部署前镜像 `h-57444ab456d0`（digest `sha256:28fd29f48acea93a5b2710ba0bff47505432bae178bbfd3cd7f65064f43bee5f`）。`deploy.sh deploy` 备份 Compose 为 `/opt/mixmaster-ai/docker-compose.rollback.yml` 并切换到新镜像；前后 Compose 文件 SHA-256 均为 `1017b4f7c349cf3070ddab1f29afaf86e549a3a2374eacf53319067b9055daab`。Compose 管理状态与容器运行镜像一致，原 `mixmaster-ai_mixmaster_ai_tmp` 卷保留；容器为 `healthy`，页面 HTTP 200。
- 真实业务验收：从服务外部以合成立体声 WAV 分别请求 `/master`，原句“在CCTV播放”“在BBC播放”“在小红书播放”均 HTTP 200，返回 24-bit WAV。FFmpeg 独立测得综合响度分别为 `-23.9`、`-22.9`、`-14.9 LUFS`，真峰值分别为 `-22.3`、`-21.3`、`-13.3 dBFS`（真峰值估计，均低于相应 `-2`、`-1`、`-1 dBTP` 上限）。BBC 加上客户明确的 `-20 LUFS / <=-2 dBTP` 后，响度测得 `-19.9 LUFS`、真峰值 `-18.3 dBFS`；单元测试另核对显式真峰值逐项优先与来源标注。短视频移动端数值在产品中标为工作参考，并非小红书官方交付标准。上述合成样本只验证当前音频链路，不构成电视台完整文件交付认证。
- 回退：在 `ttd-stage:/opt/mixmaster-ai` 恢复 `docker-compose.rollback.yml` 为 `docker-compose.yml`，再运行 `MIXMASTER_IMAGE=registry.ttd/mixmaster-ai/mixmaster-ai:h-57444ab456d0 docker compose up -d --no-build`，保留原私有 `.env` 与命名卷。此次未变更数据结构；旧镜像仍可用。

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
