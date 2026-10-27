# 手机验证

两个测试应用使用独立包名，不替换 `com.google.android.gms`。当前没有可付款的生产 APK。

## 2026-10-27 真机结果

Pura 70 / Android API 31 已安装两个测试应用。原生实验页面能打开，transaction 17 → callback 12 / Status 6
之后，返回按钮得到 Activity 1 / Status 17，取消按钮和系统返回键得到 Activity 0 / Status 16。
三条路径均无付款数据或成功结果。证据为 `verification/device-native-flow.json`。

用户自行选择 Google 账号后，授权探针收到 `io_error`。补充固定错误标识诊断后重试，确认是
`NotOkayException` / `UNREGISTERED_ON_API_CONSOLE`，没有取得令牌，也没有发起付款。
证据为 `verification/device-auth-probe.json`。下一步先完成 OAUTH_SETUP.md 中的自有客户端注册。
该结果不能判定注册后能否取得 Sierra 授权，更不能判定付款后端是否可用。

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
应用自身不发 HTTP 请求；现有微服务认证器可能联网取得授权。

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
