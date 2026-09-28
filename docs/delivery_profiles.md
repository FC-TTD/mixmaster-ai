# 单音频母带目标：规范、建议与工作参考

核对日期：2026-09-29。**播放端归一化目标不是母带交付要求。**本应用只能输出单声道或立体声 WAV，并测量输出文件的综合响度及 4× 估计真峰值；以下数值只构成当前能力范围内的音频目标，不等于平台验收、视频封装、节目元数据、对白门控或院线 DCP 合规。单音频 Luna 路径在同一次模型调用中理解完整客户需求，判断平台所属内容类型、选用下表的一套参考，并给出 DSP 参数；程序解析客户明确数值、核对预设标识并验证实际导出文件。模型服务最长等待 60 秒，超时返回可见错误。

客户明确给出的 LUFS/LKFS、dBTP、dBFS、采样率、声道、位深分别优先。缺少的响度或真峰值只从所选**一套**预设补齐；界面逐项显示“客户指定”或预设类型。LKFS 与 LUFS 在这些响度用法中可等同理解，但测量范围（整段还是对白）仍须区分。

| 类别与目的地 | 依据类型 | 自动补齐的综合响度 / 真峰值 | 边界和原始资料 |
| --- | --- | --- | --- |
| 未点名平台的**音乐流媒体** | 工作参考 | −14 LUFS / ≤−1 dBTP | 取自 [Spotify 母带建议](https://support.spotify.com/bj-en/artists/article/loudness-normalization/)和 [SoundCloud 母带建议](https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered)的同一组起点；不是整个行业的交付标准。 |
| Spotify | 母带建议 | −14 LUFS / ≤−1 dBTP | [官方母带建议](https://support.spotify.com/bj-en/artists/article/loudness-normalization/)；客户指定比 −14 LUFS 更响且未指定真峰值时，参考上限改为 −2 dBTP。Spotify 播放端 Normal/Loud/Quiet 分别按 −14/−11/−19 LUFS 归一化，不能据播放模式自动改写母带目标。 |
| SoundCloud | 母带建议 | −14 LUFS / ≤−1 dBTP | [官方母带建议](https://help.soundcloud.com/hc/en-us/articles/360053660014-Will-SoundCloud-play-my-track-at-the-level-it-s-mastered)；比 −14 LUFS 更响时真峰值参考上限为 −2 dBTP；平台播放端另做归一化。 |
| Apple Music、QQ 音乐、网易云音乐、汽水音乐、酷狗、酷我、Tidal、Amazon Music 等音乐收听服务 | **工作参考** | −14 LUFS / ≤−1 dBTP | 这是跨平台制作起点，借用 Spotify 已公开的一整组母带建议，**不是这些平台各自的官方交付要求**。[汽水音乐的 App Store 官方应用页](https://apps.apple.com/cn/app/%E6%B1%BD%E6%B0%B4%E9%9F%B3%E4%B9%90-%E9%9A%8F%E6%97%B6%E5%90%AC%E5%A5%BD%E6%AD%8C/id1605585211)将其列为音乐应用。Apple 的 [Digital Masters 技术资料](https://www.apple.com/in/apple-music/apple-digital-masters/docs/apple-digital-masters.pdf)不规定固定 −16 LUFS；发行商交付书优先。也不声称 Apple Digital Masters 认证。 |
| Apple Podcasts | 制作建议 | 约 −16 LKFS / ≤−1 dBFS 真峰值 | [Apple 官方说明](https://podcasters.apple.com/support/893-audio-requirements)容差 ±1 LU。WAV/FLAC 上传还涉及至少 44.1 kHz、声道等要求；当前预设只处理响度与真峰值，不声称完成播客文件交付。 |
| 抖音、小红书等国内短视频移动端 | **工作参考** | −15 LKFS / ≤−1 dBTP | 借用 [GY/T 377—2023](https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html)的嘈杂接收环境目标，**不是这些平台的官方母带标准**。[抖音公开上传说明](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/create/upload)未给出固定 LUFS/dBTP 组合。 |
| 爱奇艺、优酷、腾讯视频、Bilibili 等国内网络视听平台 | **工作参考** | 默认移动端 −15 LKFS / ≤−1 dBTP；明确电视端、客厅或安静收听时 −24 LKFS / ≤−1 dBTP | 根据平台类型归入国内网络视听，借用 [GY/T 377—2023](https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html)相应接收环境的一整组数值；**不是各平台公布的专属交付标准**。未说明接收环境时，界面明确写出移动端假设；客户数值逐项优先。 |
| YouTube、TikTok、Instagram Reels 等在线视频平台 | **工作参考** | −15 LKFS / ≤−1 dBTP | 为保证可产出，借用中国网络视听移动端参数作为**产品制作起点**；跨地区使用并不构成 [YouTube](https://support.google.com/youtube/answer/16619284?hl=en)或其他平台官方验收。 |
| 中国网络视听 GY/T 377—2023：嘈杂 / 安静接收环境 | 交付规范的音频子集 | −15 / −24 LKFS（各 ±2 LU）；≤−1 dBTP | [广电总局现行标准](https://www.nrta.gov.cn/art/2023/9/14/art_3715_65554.html)适用于非直播网络视听节目的制作、分发、接收；没有接收环境或明确目标时不擅选版本。 |
| 中国数字电视 GY/T 282—2014 | 交付规范的音频子集 | −24 LKFS（±2 LU）/ ≤−2 dBTP | [广电总局标准原文](https://www.nrta.gov.cn/module/download/downfile.jsp?classid=0&filename=d31ca72b07b042d883c165df58d40820.pdf)适用于数字电视制作、播出和分发，要求按完整节目测量。中央电视台、北京电视台等国内电视台的自然语言需求可以按此类识别，但不能据此声称符合台方另有的交付书；机构要求优先。 |
| EBU R 128 | 节目响度建议 | −23 LUFS / ≤−1 dBTP | [EBU R 128](https://tech.ebu.ch/publications/r128)；完整应用还涉及响度范围与元数据。 |
| BBC / DPP 电视 | 交付规范的音频子集 | −23 LUFS / ≤−1 dBTP | [BBC 文件交付规范](https://downloads.bbc.co.uk/scotland/commissioning/TechnicalDeliveryStandardsBBCFile.pdf)对非直播节目有 ±0.5 LU 容差；建议真峰值 ≤−3 dBTP，超过 −1 dBTP 会被拒收。这里的 −1 dBTP 是验收上限，仍涉及文件封装等条件。 |
| ATSC A/85 短节目 | 节目响度建议 | −24 LKFS / ≤−2 dBTP | [ATSC A/85:2026 附录 M](https://www.atsc.org/wp-content/uploads/2026/07/A85-2026-07-Annex-M.pdf)按完整短节目测量；长节目主要测对白，不能复用这个预设宣称合规。 |

## 只分类，不从平台名自动生成完整目标

| 场景 | 原因与处理 |
| --- | --- |
| 平台未公布一套固定值 | 先按**平台所属内容类型**选择有清楚来源的产品工作参考，完成音频输出；界面列出分类、环境假设和数值来源。客户指定的项目参数逐项覆盖。不得将工作参考描述为平台官方要求。 |
| EBU R 128 s2 广播内容网络分发 | [EBU 补充建议](https://tech.ebu.ch/files/live/sites/tech/files/shared/r/r128s2.pdf)以原节目 −23 LUFS 分发为首选；特定分发适配可在 −20 至 −16 LUFS，真峰值依链路确定。没有统一配对 dBTP，不能借音乐流媒体预设。 |
| Netflix 指定品牌内容、长节目、Atmos | [Netflix 近场要求](https://partnerhelp.netflixstudios.com/hc/en-us/articles/7262346654995-Post-Production-Branded-Delivery-Specifications)包含约 −27 LKFS（±2 LU）的**对白门控**测量及 2.0/5.1 的 −2 dBTP 条件；本链路只测整段综合响度，不自动声称达到此要求。其他交付类型另按 Netflix 文件。 |
| 院线电影、DCP | [DCI 数字电影规范](https://www.dcimovies.com/dci-specification/)涉及多声道、声道映射、影院校准及 DCP；没有一组通用的 LUFS/dBTP 可套在当前单轨 WAV 上。 |
| Apple Digital Masters 认证 | [Apple 技术资料](https://www.apple.com/in/apple-music/apple-digital-masters/docs/apple-digital-masters.pdf)涉及源质量及编码试听，不存在固定 LUFS 可单独证明认证；本应用输出参考 WAV。 |

用户若只写“流媒体作品”，产品按**音乐流媒体工作参考**运行；若点名爱奇艺等平台，会先按网络视听类别选参考数值，音色诉求仍照常执行。影视流媒体不会套用音乐的 −14/−1；广播内容网络分发和院线电影保留各自的能力边界。任何用户明示的数值都优先执行，输出文件由程序测量；不能达到响度与峰值组合时会报出未满足的目标。
