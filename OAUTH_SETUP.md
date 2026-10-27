# 授权探针的客户端注册

## 已实测的限制

本轮已创建自有 Android OAuth 客户端，包名与以下签名一致，并把测试账号加入测试用户列表。
手机交互授权返回 `NotOkayException: INVALID_SCOPE`；Google Cloud 控制台手动添加
`https://www.googleapis.com/auth/sierra` 时也提示该范围无效。没有取得令牌。

因此，下文注册步骤保留为实验记录，**不是可用的修复方法**。不建议反复创建客户端来重试同一个限制。
这只验证独立探针的身份和项目，不证明以 GmsCore 身份执行的内部授权一定不可行。
后者需要单独的框架集成与设备验证；当前并未完成。

2026-10-27 真机结果：现有 microG 在用户选择账号后返回
`NotOkayException: UNREGISTERED_ON_API_CONSOLE`。没有取得令牌，也没有发起付款。
探针以自己的包名/签名申请授权，未冒用 Google 或其他应用的客户端身份。

Google 的 Android OAuth 客户端配置需要包名与签名证书 SHA-1 配对：
[官方配置说明](https://support.google.com/googleapi/answer/6158849)。
结合探针当前未注册的状态和返回错误，下一步是为我们自己的探针注册客户端。
这仍不是对 Sierra scope 使用资格或支付可行性的确认。

## 当前测试构建的注册信息

| 字段 | 值 |
| --- | --- |
| 应用类型 | Android |
| 包名 | `org.microg.wallet.authprobe` |
| 签名证书 SHA-1 | `8D:0F:3D:4F:91:E2:E0:5E:E9:E1:80:09:FA:91:4A:9E:B6:C0:2B:D3` |
| 授权请求 | `oauth2:https://www.googleapis.com/auth/sierra` |

这是本机 debug 签名的公开指纹，私钥不在仓库中。更换签名密钥后必须重新核对指纹。
注册的是探针客户端；它不能自动覆盖其他包名或未来 GmsCore 发行包的客户端配置。

## 配置与复测

1. 在自己有管理权限的 Google Cloud 项目中打开 Google Auth platform，按提示配置项目和同意屏幕；
   如使用测试模式，添加自己要测试的账号作为测试用户。
2. 在 Clients 中创建 Android 客户端，填入上述包名和 SHA-1。
   不需要将客户端密钥或账号密码提交到仓库。
3. 保留当前签名，再在手机探针中点击“选择账号并检查授权”，由用户完成账号选择和授权。
4. 只收集探针自己的 `files/events.jsonl`。记录注册前后结果；如果换成其他拒绝错误，
   继续核对 scope 和客户端资格，不把注册成功当作支付授权成功。

项目保持测试模式，未启用计费。实际项目账号、联系邮箱、客户端配置下载文件和密钥不纳入开源仓库；
复现实验应使用自己的项目。即使未来得到 `token_acquired`，也需要独立验证 Google TEST 支付初始化与真实结果回传。
