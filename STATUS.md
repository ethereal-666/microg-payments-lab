# 当前状态：研究原型，不能付款

截至 2026-10-27（香港时间），没有取得 Google TEST 支付数据，没有修复 Chrome 的实际充值流程。
开源代码用于复现协议、原生交接和授权限制，不能宣传为已实现 microG Google Pay。

| 项目 | 实际结果 | 证据 |
| --- | --- | --- |
| Wallet transaction 17 / callback 12 ABI | 5 项单元测试通过 | verification/protocol-test-result.json |
| UID 绑定、请求校验、一次性 PendingIntent、错误与取消 | 13 项 Robolectric 测试通过 | verification/native-flow-result.json |
| 授权诊断脱敏 | 8 项 Robolectric 测试通过 | verification/native-flow-result.json |
| 独立服务进程 → 实际 Binder → 原生 Activity → 返回 | Pura 70 三条路径通过 | verification/device-native-remote.json |
| 完整 Huawei GmsCore APK | 构建、签名验证通过；未安装 | verification/provider-build-result.json |
| 独立授权探针、自有 Android OAuth 客户端 | 注册后交互请求返回 INVALID_SCOPE，无令牌 | verification/authorization-route-result.json |
| 非交互授权观测 | 单独记录，需要授权不能当作成功 | verification/device-auth-noninteractive.json |
| microG 委托 Sierra 授权 | 真机取得令牌，Google tokeninfo 确认 scope | verification/device-auth-delegated.json、verification/device-buyflow-initialize.json |
| 网页买单初始化实验 | HTTP 200，但 HANDLE_UI_ERROR（5），无有效付款页 | verification/device-buyflow-initialize.json |
| 开源组件复用 | 三个 Bender3 UI/状态源文件原样抽到共享模块 | research/opensource-reuse-plan.json |
| Google TEST 支付数据、Chrome 商户集成 | 未实现/未通过 | project.json |

## 实际阻碍

1. 普通独立客户端的 Sierra 授权失败，但现有 microG 的用户同意委托接口已经取得有效 Sierra 令牌。
   因此当前不再以授权失败为首要阻碍；Cloud 客户端注册本身仍不足以取得权限。Google 的[公开 scope 说明](https://developers.google.com/identity/protocols/oauth2/scopes)
   也不能替代实际服务端资格验证。
2. 手机已安装 microG 的签名与本机构建不同。没有相同私钥，不能普通覆盖更新；卸载认证器可能丢失账号状态，
   本轮没有这样操作。证据为 verification/provider-install-preflight.json。
3. 即使解决框架内授权，网页买单初始化、商户身份绑定、Google 返回的真实支付数据仍需实现。
   上游 Bender3 内购验证与网页付款不是同一个入口，不能将内购回执当作网页支付令牌。

## 可继续研究的路线

已验证在原手机保留现有 microG 的情况下取得授权。下一步基于上游 Bender3 的模型、UI 和状态引擎实现网页买单适配。
本轮独立探针的失败不能推广为此路线必然失败，也没有证据证明此路线一定能在原机无损安装并付款。
下一阶段验收必须是 Google TEST 环境的真实结果；测试用回调、界面或成功占位数据不满足验收。

仓库包含 Apache-2.0 代码、microG 补丁与脱敏结果，不包含 Google APK/反编译源码、账号、令牌或签名私钥。

用户要求转向开源复用后，已停止继续逐字段在线探测。模拟器已按用户要求移除，真机 microG 未替换。
