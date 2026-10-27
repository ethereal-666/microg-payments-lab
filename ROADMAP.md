# 开发路线与验收

## P0：可复现的请求与回调

协议与原生错误交接的代码已实现，独立测试应用的 Pura 70 实机验证已通过。先正确保留 SDK 20.0.0 请求字段，验证 transaction 17 / callback 12，
并记录 Google 原生实现的界面唤起方式。接口测试与实机结果分别记录。

验收：协议测试通过，未知字段不破坏外层 Binder 参数；金额、币种和商品项未丢失；
原生界面所需的 Status 6 / PendingIntent 能通过回调传递。该阶段不具备付款能力。已通过 5 项协议测试及 13 项原生交接测试；界面目前只返回不可用或取消。

## P1：基于已有开源实现移植网页买单

2026-10-27 真机已通过 microG 的现有委托授权接口取得 Sierra token，Google tokeninfo 返回 200 并确认 scope。
独立普通 OAuth 客户端的 INVALID_SCOPE 仍然属实，但不能再将其列为全部授权路线的结论。
初始化返回 HTTP 200 后，进一步解码的指令是 HANDLE_UI_ERROR（5），没有有效原生页面，不能记为初始化成功或能付款。

根据用户要求，冻结逐字段在线尝试，改为先复用有来源的代码。检索与源码核对清单见
[research/opensource-reuse-plan.json](research/opensource-reuse-plan.json)。本次没有找到完整可直接替代 GMS 的网页付款开源服务。

| 能力 | 复用来源 | 需要新增的适配 |
| --- | --- | --- |
| protobuf 与代码生成 | microG PR #3507 的 Purchase.proto / Wire | 网页 buyflow 独有的请求与响应模型；不能将 IAP 字段硬套进去 |
| 原生组件与布局 | 同一 PR 的 PaymentsScreen、ComponentTreeManager | 网页响应到公共页面模型的转换 |
| 交互状态 | 同一 PR 的 EventEngine | 网页会话的输入、提交与结果回传 |
| 会话与传输结构 | PaymentContext | 分离买单端点、账号授权、商户上下文；清理上游调试数据输出后才能用于支付 |
| 测试商户请求 | Google Android quickstart | 作为验收输入，示例本身仍依赖 GMS |
| 最终 ECv2 测试数据验证 | Tink paymentmethodtoken | 独立测试商户侧验签；不能替代框架付款服务 |

已将三个原有 UI/状态源文件原样移入 wallet-bender3-ui 共享模块，保持包名和公开函数不变，完整框架改为依赖该模块。
源文件 SHA-256 和与固定上游版本逐字节一致的核对结果记录在 verification/shared-ui-source-integrity.json。

后续移植必须先写清请求/响应适配契约，再接共享渲染器。每个缺失字段都需要开源定义或明确协议证据；
手写实验报文只保留为失败诊断，不进入生产支付路径。验收仍要求 Google TEST 真实支付数据及浏览器回传。

## P2：Android 界面与 Chrome 集成

在后端可行后实现：账号选择、付款信息呈现、用户确认、验证跳转、取消、超时、
Activity 重建以及 PendingIntent 结果回传。校验 Binder 调用身份与商户 origin 的来源，
不要只信任请求里声称的包名或 origin。

验收：由测试商户发起、用户确认、Google 返回、Chrome 收到的整条 TEST 路径可复现；
取消与失败能完成回调，错误路径不产生成功结果。前面的接口单元测试不能替代该验收。

## P3：华为设备适配与发布评估

至少在两种设备/系统组合记录完整兼容性；验证是否需要 root、系统修改或固定 Google 版本。
生产环境验证单独计划，任何真实付款由用户自行最终确认。

候选交付形态优先是可审阅的 microG 上游补丁；独立伴随应用是否需要，再由 P1/P2 决定。
NFC 与 HarmonyOS NEXT 作为独立后续项目评估。
