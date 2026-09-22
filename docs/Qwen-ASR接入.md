# Qwen Filetrans 转写与时间戳

模型：`qwen-audio-3.1-asr-flash-filetrans`。使用 Filetrans 异步接口获取转写与时间戳。

## 已验证的请求

提交地址：`POST https://maas.qianwenaiapi.com/api/v1/services/audio/asr/transcription`。

请求头使用 `Authorization: Bearer $DASHSCOPE_API_KEY`、`Content-Type: application/json`、`X-DashScope-Async: enable`。

```json
{
  "model": "qwen-audio-3.1-asr-flash-filetrans",
  "input": {"file_urls": ["音频公网地址"]},
  "parameters": {"channel_id": [0]}
}
```

本模型实测使用复数 file_urls 数组，只识别声道 0。没有传 enable_words、format 或 sample_rate，也返回了句级和词级时间戳。勿直接套用其他模型文档的单数 file_url。本入口使用上面的固定域名，不依赖 SFM_WORKSPACE_ID；TTS 继续使用业务空间变量。

提交返回 task_id；通过 `GET https://maas.qianwenaiapi.com/api/v1/tasks/{task_id}` 查询。PENDING/RUNNING 继续查询；SUCCEEDED 后下载 transcription_url 中的 JSON。下载不附带 API Key。

## 运行与恢复

```bash
python scripts/asr_qwen.py --response-file runs/voice_01/response_private.json --run-dir runs/asr_01
python scripts/asr_qwen.py --run-dir runs/asr_01 --resume
```

也可提供 --audio-url；本地音频需先放到你控制的可访问存储，脚本不自动上传。音频和结果 URL 均可能过期，及时保存结果。--max-wait 默认 300 秒，控制轮询等待；单次网络请求另有 120 秒超时。

每个运行目录提交一次。程序在 POST 前记下提交开始状态，POST 后立即保存 task.json。请求超时导致提交结果不明时，禁止自动重复提交；如从服务端取得 task_id，可执行：

```bash
python scripts/asr_qwen.py --run-dir runs/asr_01 --resume --task-id '已知任务ID'
```

--resume 不接受新音频来源。成功状态或下载结果已缓存时直接复用。网络异常、任务失败会报错；不偷偷切换模型，也不自动重提。FAILED 需查明原因后再另建目录。

## 输出与校对

- task.json：提交响应及任务 ID。
- status_private.json、result_private.json：任务状态及原始结果，可能包含临时地址，保留在被 Git 忽略的 runs 下。
- alignment.json：列表结构，每句含 start/end/text/words，每词含 start/end/text，毫秒转换为秒。检查时间范围、句词顺序及包含关系；不按字数伪造时间。
- transcript.txt：识别文字。
- subtitles.draft.srt：按原始句段导出的字幕草稿；修正专名、分行与长句后使用。
- summary.json：句词数量、单位及 needs_review 状态。

alignment.json 保存识别文字及时间戳，动画 timeline.json 保存画面事件。设计者仍需把动作事件关联到校对后的语义时间。音轨剪辑或拼接后应重新定位或准确映射时间。

## 2026-09-22 实测

使用已有的一分钟 Jev 配音，48kHz、双声道，原始长度 60.48 秒；识别声道 0。

- task_id：`98423451-0f11-418d-be64-3c829f509060`。
- 提交 request_id：`9bdad19f-42e4-99ca-bb40-db61fcc2a6c4`。
- 最终状态 SUCCEEDED；返回 13 句、131 个词条。
- 词条起始时间单调，所有词条时间都处于音频长度以内。
- 例如“最近”为 960–1280ms，“有个”为 1280–1520ms。
- Jev 被识别成 Japh/Jave，“接进”被识别成“接近”，仍须对照原稿校正。时间戳结构检查不等于人工逐词同步验收。

这是一次样本测试，不是准确率或性能基准。

## 参考文档

[官方 Qwen-ASR API 文档](https://help.aliyun.com/en/model-studio/qwen-asr-api-reference)可参考异步提交、轮询与时间戳字段。本项目采用上方已实测成功的模型名和 file_urls 请求结构。
