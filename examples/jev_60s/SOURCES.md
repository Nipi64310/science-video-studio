# 本片的事实依据

整理日期：2026-09-22。

## Jev 接收的是什么

TypeSafe 官方文档介绍的是结构化判断接口：提供 state、问题以及所需结果类型，输出可交给程序使用的判断。它不是普通的聊天助手。Choice 类问题先定义候选项，模型在选项中判断。

本片的“往左、往右、原地等”是自编教学选项，不是官方游戏请求日志。

来源：https://docs.typesafe.ai/introduction
来源：https://docs.typesafe.ai/primitives/choice

## 打游戏的前提

官方发布文章包含 Doom 演示，并明确说明输入是整理后的文字状态，而不是直接输入游戏图像；文章还指出传统非 AI 游戏机器人可以玩得更好。因此本片专门讲“模型选动作，代码执行”，不说它自己看屏幕、按键或包办整个 Agent。

来源：https://typesafe.ai/blog/introducing-system-one-models-and-jev

## 接到 Agent 工作流

官方 intent-routing 文档介绍先判断意图，再交给后续处理器的用法。处理器可以是程序逻辑、工具或其他模型。本片搜索与模型 A/B 的图是这一模式的教学简化，并非一次真实请求的追踪记录。

来源：https://docs.typesafe.ai/patterns/intent-routing

## 为什么还可能掉坑

输出值属于允许的候选集合，只能说明格式符合要求，不能证明该选择正确。本片掉坑是原创逻辑反例，不是 Jev 实测失败案例。普通大模型也能输出结构化判断；没有同任务对照测试，不能断言 Jev 在所有场景更快、更便宜或更准确。

来源：https://docs.typesafe.ai/primitives/choice
来源：https://docs.typesafe.ai/primitives/score

## 音频生产

本片实际使用 Qwen-Audio-3.1-TTS-Next，传入用户认可的参考音，通过 @voice1 指定主讲人，一次生成 60.48 秒音频。音乐与提示音属于同次音频创作请求。接口请求成功不等于声音复刻效果已经人工验收。

来源：https://help.aliyun.com/zh/model-studio/audio-generation-api
