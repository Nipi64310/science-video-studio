# Qwen ASR 接入与字幕对齐

模型：`qwen-audio-3.1-asr-flash-message`。请求地址：`https://maas.qianwenaiapi.com/api/v1/services/aigc/multimodal-generation/generation`。

## 实测状态

2026-09-22 使用授权测试凭证调用。以下尝试都返回 HTTP 400，错误码 `InvalidParameter`，消息 `url error, please check url`：

- 接入示例 `input_audio.data`，12 秒、16kHz 单声道 WAV 的 Data URI；请求 ID `d930ba41-39c3-9cbd-9258-db5a31b129e8`。
- 同一结构，已有 Next 配音下载 URL；请求 ID `b9b7d4c7-196e-98c5-8d36-e26a9fd20ae3`。该 URL 在本地直接读取返回 HTTP 200。
- 同一结构，Qwen 官方仓库示例 WAV URL；请求 ID `5f7c475a-4e33-9288-bebd-6776ff93710e`。
- 通用 DashScope `audio` 结构，Data URI 与官方示例 URL 也均失败；后者请求 ID `59ea648e-41c6-9ac5-8e7c-6fcbae0d67d6`。

- 业务空间专属入口，原配音 URL、按实际音频填写 48000Hz，也返回相同错误；请求 ID `07748367-857b-9798-bca4-60ca52745442`。

这证明请求已到服务端，但不能证明模型成功识别。目前未确认该接入模型的实际输入契约或时间戳能力，需服务方结合请求 ID 排查。没有把失败记录包装成模型能力结论。

## 代码使用

`python scripts/asr_qwen.py --audio-url '可访问的WAV地址' --sample-rate 16000 --output runs/asr/transcript.json`

认证仅从 `DASHSCOPE_API_KEY` 获取。默认 `--protocol message` 沿用给定接入示例；`--protocol dashscope` 使用通用文档的 `audio` 字段。一次请求、180 秒超时、禁止认证重定向、不自动重试，不打印音频地址或认证值。`--response-file` 可以从 Next 缓存响应读取 URL。此接口默认地址不使用业务空间变量；TTS 继续读取业务空间变量。

支持的成功响应解析位置为 `output.choices[0].message.content` 的字符串或 text 列表；未知结构保留响应并报错。输出包含 `alignment_status: not_aligned`；不按字数摊分时间，也不伪造 SRT。响应请保存在被 Git 忽略的 runs 下。

## 与字幕的关系

Qwen 转写入口用于内容核对。精确字幕仍需时间戳：当前保留可选 `scripts/align_whisper.py`，依赖单列在 `requirements-alignment.txt`。`requirements-audio.txt` 不再要求 Whisper。历史示例的已校对时间轴与字幕可直接使用。

通用文档区分 OpenAI 兼容格式与 DashScope 格式；其中 Filetrans 的 `enable_words` 属于另一个接口，不能直接当作本模型已支持的参数。

参考资料：

- [阿里云 Qwen-ASR API 文档](https://help.aliyun.com/en/model-studio/qwen-asr-api-reference)：DashScope 的 content 使用 audio 字段；OpenAI 兼容结构使用 input_audio。
- [Qwen 官方 ASR 示例代码](https://github.com/QwenLM/Qwen3-ASR/blob/main/examples/example_qwen3_asr_transformers.py)：本次连通性排查使用其中的公开中文 WAV 地址。
