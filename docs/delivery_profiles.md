# 母带交付预设与官方依据

核对日期：2026-09-29。这里列出当前单音频 WAV 链能自动执行的**响度与真峰值子集**。LKFS 与 LUFS 在 EBU R 128 中为等价单位。预设不是整套播出、编码、元数据或平台验收认证。客户明确给出的每项数值优先，缺项只从**同一个**已识别预设补齐。

| 识别词 / 场景 | 默认综合响度 | 默认最大真峰值 | 官方依据与边界 |
| --- | ---: | ---: | --- |
| 未指定平台的音乐流媒体、`流媒体` | -14 LUFS | -1 dBTP | 应用参考预设，依据 [Spotify](https://support.spotify.com/bj-en/artists/article/loudness-normalization/) 与 [SoundCloud](https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered) 的同组母带建议；并非所有平台统一标准。 |
| Apple Music、QQ 音乐、网易云音乐、酷狗、酷我、Tidal、Amazon Music | -14 LUFS | -1 dBTP | **产品工作参考，不是这些平台公布的统一标准。**沿用 [Spotify 官方母带建议](https://support.spotify.com/bj-en/artists/article/loudness-normalization/)作为一整组可追溯的音乐母带起点；客户有发行方交付书时逐项覆盖。Apple Music 的 [官方交付资料](https://help.apple.com/itc/videoaudioassetguide/en.lproj/static.html)并未指定固定的 -14 LUFS。 |
| Spotify | -14 LUFS | -1 dBTP | [Spotify 母带建议](https://support.spotify.com/bj-en/artists/article/loudness-normalization/)；若客户明确要求比 -14 LUFS 更响、又未指定真峰值，则配套参考上限为 -2 dBTP。 |
| SoundCloud | -14 LUFS | -1 dBTP | [SoundCloud 母带建议](https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered)；比 -14 LUFS 更响时配套参考上限为 -2 dBTP。 |
| Apple Podcasts | -16 LUFS | -1 dBTP | [Apple Podcasts 音频建议](https://podcasters.apple.com/support/893-audio-requirements)；这里只处理音频响度和峰值，仍导出 WAV。 |
| EBU R 128 | -23 LUFS | -1 dBTP | [EBU R 128（2023）](https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128.pdf)；未核验响度范围、元数据或分发链。 |
| BBC/DPP 电视 | -23 LUFS | -1 dBTP | [BBC 文件交付规范](https://downloads.bbc.co.uk/scotland/commissioning/TechnicalDeliveryStandardsBBCFile.pdf)；不生成 AS-11 等视频交付格式。 |
| 中国数字电视 GY/T 282 | -24 LUFS | -2 dBTP | [广电总局 GY/T 282—2014](https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=d31ca72b07b042d883c165df58d40820.pdf)；机构另有交付书时以交付书为准。 |
| 中国网络视听 GY/T 377，嘈杂环境 | -15 LUFS | -1 dBTP | [广电总局 GY/T 377—2023](https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf)；适合车载、户外等环境。 |
| 中国网络视听 GY/T 377，安静环境 | -24 LUFS | -1 dBTP | [同一规范](https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf)；没有环境或目标响度时，这两版不能自动择一。 |
| 抖音、国内短视频移动端 | -15 LUFS | -1 dBTP | **移动端工作参考，不是抖音官方母带标准。**采用 [GY/T 377—2023](https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=0e71703f4538412db1a08f2089101dda.pdf)嘈杂接收环境的一整组数值；[抖音开放平台上传说明](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/upload)未给出这一组固定数值。 |
| ATSC A/85 短节目 | -24 LUFS | -2 dBTP | [ATSC A/85:2026-07 附录 M](https://www.atsc.org/wp-content/uploads/2026/07/A85-2026-07-Annex-M.pdf)；长节目需对白门控测量，当前链路不支持。 |

以下是常见目的地，但**不能据其名称自动填一组固定 LUFS / dBTP**：

| 目的地 | 当前处理 | 原因 / 官方资料 |
| --- | --- | --- |
| YouTube、Bilibili、优酷、爱奇艺、腾讯视频等 | 客户同时提供 LUFS 与 dBTP 时按其数值执行；缺项不借 Spotify 数值 | 当前没有核实到适用于本单音频交付的同套官方固定数值；[YouTube 官方帮助](https://support.google.com/youtube/answer/16619284?hl=en)不提供该数值组合。 |
| Apple Digital Masters 认证 | 仅能制作参考 WAV，不声称认证 | [Apple 交付指南](https://help.apple.com/itc/videoaudioassetguide/en.lproj/static.html)要求高质量原生 24-bit 来源、允许的采样率及 AAC 编码试听；[Apple 技术说明](https://www.apple.com/in/apple-music/apple-digital-masters/docs/apple-digital-masters.pdf)未规定单一母带 LUFS。不能把 16-bit 来源升位伪装为合格源。 |
| Netflix 长节目 / Atmos | 不自动套用 LUFS 目标 | [Netflix 交付要求](https://partnerhelp.netflixstudios.com/hc/en-us/articles/7262346654995-Post-Production-Branded-Delivery-Specifications)使用对白门控、声道和文件交付要求；当前链路只有整体综合响度测量，不能宣称完整合规。 |
| ATSC A/85 长节目 | 需客户明确数值；不声称 A/85 认证 | [ATSC A/85:2026-07](https://www.atsc.org/wp-content/uploads/2026/07/A85-2026-07.pdf)区分长节目对白测量和短节目整体测量。 |
| 院线电影 / DCP | 不自动生成 LUFS / dBTP 预设 | [DCI 数字电影规范](https://www.dcimovies.com/dci-specification/)涉及多声道 PCM、声道映射、DCP 与影院校准；当前单声道/立体声 WAV 链不能交付或验证 DCP，也不存在可据“电影”二字套用的统一综合响度。电影流媒体版按具体发行方交付书处理。 |

这些预设只补充标准中**可由当前单音频链可靠执行**的项目。没有统一值的采样率、声道和文件格式，保留源文件与 UI 设置；客户明确指定的格式参数仍按要求校验。达到某个 LUFS 与真峰值不等于通过平台全部验收。

听感诉求也按能力边界执行：明确要求“齿音过重”时使用动态齿音控制；“音色太暗 / 高频不足”用宽高架提亮；“高频弱化 / 削弱高频”用宽高架衰减。没有音频试听或参考曲，Luna 只能根据文本和频谱统计给出起点；后端会确保这些明确的方向不会退化为中性参数，最终仍应试听确认。
