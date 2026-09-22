# Jev 三分钟版：事实说明

核对日期：2026-09-22。视频画面是原创教学动画；没有调用 Jev 做性能或正确率测试。下列概括是这期实际采用的资料，不要求读者自行整理网页。

1. **定位与输出**：TypeSafe 把 Jev 定位于供软件使用的结构化判断，提供 Choice、Score、Noul 三类问题。视频将其解释为选项、按标准评分、是非条件的概率。不把它当完整聊天助手。
   来源：https://docs.typesafe.ai/introduction
2. **游戏输入**：官方 Doom 演示使用整理后的文字状态，并非游戏截图。发布文章还承认传统游戏机器人可以玩得更好。视频未声称它打游戏超越传统程序。
   来源：https://typesafe.ai/blog/introducing-system-one-models-and-jev
3. **Choice**：开发者定义候选集合，结果包括选中的选项与选项分布。格子图中的左、右、等是原创教学例子。
   来源：https://docs.typesafe.ai/primitives/choice
4. **Score**：先定义有序档位，结果可以处于档位之间。视频给出的 0.1/0.7/0.2 是假设档位概率，对应 1.1 分，不是危险有 11%。
   来源：https://docs.typesafe.ai/primitives/score
5. **Noul**：数值表示回答“是”的概率，不是问题对象的程度；没有另外的 confidence 字段。0.9 是原创示意，不是实测数据。
   来源：https://docs.typesafe.ai/primitives/noul
6. **普通大模型与 Jev**：普通模型也能输出结构化结果。官方描述 Jev 围绕判断任务设计，使用并行输出；本片仅归因介绍，不把厂商速度数字当作独立实测。
   来源：https://typesafe.ai/blog/introducing-system-one-models-and-jev
7. **Agent 分流**：判断后可以交给确定性代码、其他模型或人工。是否真正省钱，需包含额外路由调用和错误后的返工成本。这是本片提出的测试建议，不是已有测量结论。
   来源：https://docs.typesafe.ai/patterns/intent-routing
8. **置信度**：Choice/Score 的 confidence 概括选项分布；不能保证单次回答正确。是否补信息或转人工由程序策略决定。视频中的 0.36/0.34/0.30 是假设分布。
   来源：https://docs.typesafe.ai/confidence
9. **掉坑**：原创逻辑反例：符合允许的选项集合，不等于当前选择正确。不能据此声称 Jev 实测发生了某次故障。

本版删去了原方案中的社区项目转述、具体报价和性能倍数，集中讲工作机制、三种判断、工作流与测试方法。不是否定这些材料，而是避免三分钟内容过散。
