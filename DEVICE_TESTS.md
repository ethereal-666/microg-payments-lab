# 手机验证

两个测试应用使用独立包名，不替换 `com.google.android.gms`。当前没有可付款的生产 APK。

## 2026-10-27 真机结果

Pura 70 / Android API 31 已安装两个测试应用。原生实验页面能打开，transaction 17 → callback 12 / Status 6
之后，返回按钮得到 Activity 1 / Status 17，取消按钮和系统返回键得到 Activity 0 / Status 16。
三条路径均无付款数据或成功结果。证据为 `verification/device-native-flow.json`。

用户自行选择 Google 账号后，授权探针收到 `io_error`。补充固定错误标识诊断后重试，确认是
`NotOkayException` / `UNREGISTERED_ON_API_CONSOLE`，没有取得令牌，也没有发起付款。
初始证据为 `verification/device-auth-probe.json`。

后续已创建自有 Android OAuth 客户端并添加同一账号为测试用户；交互授权返回 `INVALID_SCOPE`，
Cloud 控制台也拒绝 Sierra scope。后续证据见 `verification/authorization-route-result.json`。
注册客户端没有解决普通客户端路线的问题。后续通过现有 microG 委托接口取得有效 Sierra 令牌，Google tokeninfo 已确认 scope；
初始化实验的 HTTP 200 被进一步解码为 HANDLE_UI_ERROR（5），没有有效付款页。见 verification/device-buyflow-initialize.json。

最初 harness 在应用进程内本地 transact。升级后的服务位于 `:wallet` 独立进程，
3 项 instrumentation 已验证真实 IPC、PendingIntent 和页面返回；新证据是 `verification/device-native-remote.json`。
不要把旧的本地 transact 记录标为跨进程测试。

## 无需人工点击的复现

先运行 README 中的 `tools/lab.py verify` 构建应用与 Android 测试 APK，然后：

```bash
python tools/device.py native --serial SERIAL
python tools/device.py auth --serial SERIAL
```

第二条只尝试探针已经可见的唯一账号，不选择多个账号、不批准新的授权，也不输出账号标识。
结果分开记录“观测用例完成”和“OAuth 是否成功”；需要交互时返回 `interactive_authorization_required`。
交互授权的错误结果应与该非交互观测分别保存。

本机发现 ActivityScenario 的 EmptyActivity 偶尔会占据前台，导致 Espresso 无法获得窗口焦点。
测试改用平台 Instrumentation 直接启动；每轮只停止测试应用及其 runner，清理自己创建的 Activity。
设备报告包含实际安装的应用/测试 APK 校验值，旧版本报告不能直接用于新版 APK。

先用 `adb devices` 确认用户连接并授权的手机，再将下面的 `SERIAL` 替换成该设备序列号。

## 原生唤起与返回

```bash
adb -s SERIAL install -r artifacts/wallet-web-harness-debug.apk
adb -s SERIAL shell am start -n org.microg.wallet.lab/.HarnessActivity
```

点击 Test native UI and return flow。预期：

1. 实际 OwServiceImpl 收到 transaction 17，callback 12 返回状态 6。
2. 打开实验模块的“付款暂不可用”窗口；这不是 Google 选卡或付款界面。
3. 点击返回：Activity result 为 1，状态为 17；点击取消：Activity result 为 0，状态为 16。
4. 旋转屏幕、返回和重新测试均不得产生 RESULT_OK。

只读取该测试应用自己的事件：

```bash
adb -s SERIAL shell run-as org.microg.wallet.lab cat files/events.txt
```

这验证 Android 上的 Binder/Activity 交接，不验证 Chrome 真实商户集成或 Google 付款后端。
单元测试已覆盖调用 UID 不一致、包名伪造、错误 origin、过期请求和回调死亡的处理。

## 支付授权是否可取得

```bash
adb -s SERIAL install -r artifacts/wallet-auth-probe-debug.apk
adb -s SERIAL shell am start -n org.microg.wallet.authprobe/.AuthProbeActivity
```

用户自己点击“选择账号并检查授权”，选择 Google 账号，并自行处理可能出现的授权页面。
目标 scope 是 microG 现有支付验证代码使用的 `oauth2:https://www.googleapis.com/auth/sierra`。
普通 AuthProbeActivity 不发 HTTP 请求；现有微服务认证器可能联网取得授权。
DelegatedAuthActivity 是单独的联网研究入口，结果与普通客户端观测分开保存。

结果分类：

- `token_acquired`：该测试应用取得了此 scope 的令牌；仅说明授权这一步成功。
- `access_denied` / `authenticator_error`：认证权限或认证器拒绝；保留分类和错误码继续定位。
- `io_error`：认证器将失败包装为 I/O 错误，不一定是网络断开；若包含 `io_hint` 或
  `auth_error_hint`，它们只包含固定白名单标识，不包含原始异常或任意服务端文字。
- `interactive_authorization_required`：认证器仍返回交互需求，尚不能当作成功。
- `cancelled` / `no_token`：未取得令牌。

仅收集不包含凭据的诊断：

```bash
adb -s SERIAL shell run-as org.microg.wallet.authprobe cat files/events.jsonl
```

不要导出完整认证 Bundle、账号数据库或 token。取得 scope 的授权后，下一步仍需实现
Google TEST 支付初始化、商户上下文和真实结果返回，不能据此宣称能付款。

## 清理

```bash
adb -s SERIAL uninstall org.microg.wallet.lab
adb -s SERIAL uninstall org.microg.wallet.authprobe
```

清理测试应用不会主动修改现有 microG 的安装或 Google 账号；授权撤销由系统账号设置管理。

## 已冻结的委托授权/初始化实验

DelegatedAuthActivity 使用 microG 现有的 package delegation 功能，固定请求 Sierra scope。
它不接收任意账号、scope、包名或证书输入；需要同意的 microG 页面不会被程序自动批准。
注意 microG 的身份委托权限本身比单个 scope 更广，不能将其描述成单个 scope 的系统权限。

已取得的真实结果为：Google tokeninfo 200、Sierra scope 存在；网页买单返回 HANDLE_UI_ERROR，未获得支付数据。
按用户要求，暂不继续逐字段在线尝试。先基于已有开源实现补齐网页适配契约，再恢复真机验收。
原始响应只保留在测试应用私有、禁止备份的目录中，不进入项目仓库。

wallet-bender3-ui 的源代码来自固定 microG 上游版本，三个文件逐字节保持一致；模块抽取已通过完整 Huawei 框架构建。
这项构建验证不代表它已连接网页支付后端，也不代表真机已安装该框架。
