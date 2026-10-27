# microg-payments-lab

面向华为 Android 兼容系统的 **Google Pay 网页付款兼容性实验工程**，Apache-2.0 开源。
**当前不能付款，不是可用的 Google Pay 解决方案。** 本仓库公开代码和失败证据，便于继续研究。
最新结论与验收边界见 [STATUS.md](STATUS.md)。

第一阶段研究 Chrome → microG → Google Pay 在线付款，设备基线是 Pura 70、
HarmonyOS 4.2.0.242 / Android SDK 31。NFC 刷卡和 HarmonyOS NEXT 不属于当前阶段。

## 已有基础

- microG `v0.3.17.252432` 的实验补丁：请求 transaction 17、回调 transaction 12、
  `WebPaymentDataRequest` / `WebPaymentData`，以及 Cart 和 LineItem 的数据模型。
- 独立构造 Wallet SDK 报文的协议测试：保留金额、币种、商品项、未知字段和外层参数；
  检查单向 Binder 调用、错误回调、携带 PendingIntent 的原生界面回调。
- `wallet-web-core`：实际 OwServiceImpl 的调用方 UID 绑定、请求校验、独立且不可修改的一次性
  PendingIntent，以及 Activity 的过期、错误和取消结果；目前界面只说明付款不可用。
- `wallet-web-harness`：服务运行在独立 `:wallet` 进程，通过真实 Binder transaction 17 / callback 12
  打开 Activity。3 项 Pura 70 真机 instrumentation 测试通过；不替换手机 microG，不访问账号或网络。
- `wallet-auth-probe`：用户主动选择 Google 账号后，通过现有认证器请求 Sierra OAuth 授权；
  只保存授权结果分类，不保存账号名、令牌或服务端错误原文。它不发起付款。
- `native-port-probe/`：在独立 Android 应用中测试官方钱包类加载与服务初始化。
  它没有网络或账号权限，不发送付款请求；Google 24.40.34 的实验性上下文适配是版本特定的。
- `research/` 保存本轮公开资料检索结果；`verification/` 保存脱离付款数据的实验结果。

现有服务对有效请求返回 `RESOLUTION_REQUIRED`，Activity 再返回 `API_NOT_CONNECTED` 或取消；
`isReadyToPay` 仍然返回 false。原生提示页面及错误、取消、系统返回已在 Pura 70 真机验证。
独立授权探针最初收到 `UNREGISTERED_ON_API_CONSOLE`。注册自有 Android OAuth 客户端、添加测试账号后，
交互请求返回 `INVALID_SCOPE`，Cloud 控制台也拒绝添加 Sierra scope。没有取得令牌。
仅注册 OAuth 客户端不足以解决授权，详见 [OAUTH_SETUP.md](OAUTH_SETUP.md)。
这不能推断以 GmsCore 自身身份运行时的授权结果；该集成路线尚未实机验证。
完整 Huawei GmsCore APK 已构建，但与手机已安装版本的签名不同，未覆盖安装。
尚未接入能付款的 Google 后端。
一次类加载、界面唤起或 OAuth 授权成功都不代表支付已可用。

## 研究结论

截至 2026-10-27，本轮查询未找到可验证的、完整实现华为 microG 原生网页 Google Pay 的公开项目。
这是检索范围内的结论，并非证明所有公开或私有实现都不存在。

| 现有工作 | 可借鉴的部分 | 尚不能据此认定什么 |
| --- | --- | --- |
| [microG #361](https://github.com/microg/GmsCore/issues/361) | 钱包支持的长期讨论 | 该讨论多涉及 NFC，不能直接推断网页付款的全部限制 |
| [microG #3507](https://github.com/microg/GmsCore/pull/3507) | 内购安全验证、Bender3 界面、会话与提交代码 | 不等于 Chrome WebPaymentData 流程已实现 |
| [Play Integrity workarounds](https://github.com/D3SOX/microg-play-store-workarounds) | rooted custom ROM 的认证和 Play Store 实验 | 不是支付服务实现，文档基线也不是本机无 root 的 HarmonyOS |
| [GrapheneOS sandboxed Google Play](https://grapheneos.org/features#sandboxed-google-play) | 通过兼容层运行官方服务的另一条路线 | 不是 microG 的付款后端，也不是可直接安装到 HarmonyOS 的兼容层 |
| [Google Android quickstart](https://github.com/google-pay/android-quickstart) | 商户请求格式和结果处理 | 示例仍要求设备具备 Google Play 服务 |

当前上游与本轮检查的 ReVanced 钱包实现仍返回不可支付，未实现 `loadWebPaymentData`。
另有名为“Google Pay India”的历史 PR，不能把应用放行或印度支付应用支持当作全球银行卡钱包实现。

优先路线是基于 microG 逐步实现协议和会话，以 Google 的 TEST 环境验证；
官方二进制加载保留为对照实验。之前两次实机加载分别卡在全局上下文和 Chimera ModuleManager。
目前没有证据证明完整原生代码可以通过薄适配层直接运行。

## 复现

工程本身只保存自己的源码、补丁、公开研究索引与测试结果。Google APK、反编译源码、
Android SDK、签名密钥及上游 checkout 都保留在本机并排除在版本控制之外。

在工程根目录准备好 Android SDK 后：

```bash
# 需要 Android SDK Platform 35 和 Build Tools 35.0.0。
# 固定上游提交，应用补丁，并写入 SDK 路径；重复执行不会重置已有工作。
python tools/bootstrap.py --sdk /absolute/path/to/android-sdk
python tools/lab.py verify --gmscore GmsCore --java-home /usr/lib/jvm/java-17-openjdk
python tools/lab.py status
python tools/lab.py probe-summary verification/native-probe-context-initialized.txt
# 仅安装独立测试应用及 instrumentation，不替换 com.google.android.gms。
python tools/device.py native --serial YOUR_AUTHORIZED_DEVICE_SERIAL
# 仅复测探针已经可见的唯一账号；不自动批准新授权。
python tools/device.py auth --serial YOUR_AUTHORIZED_DEVICE_SERIAL
```

当前验证包括 5 项协议测试、13 项原生交接流程测试、8 项授权诊断测试，以及两个测试 APK 的构建。
APK 会复制到本地 `artifacts/`，校验值写入 `verification/artifacts.json`；APK 不纳入源码仓库。
接手机后的步骤见 [DEVICE_TESTS.md](DEVICE_TESTS.md)。
`device.py` 会检查 instrumentation 的实际完成结果，不能把 ADB 退出码 0 当作测试通过；
授权观测用例通过也不能当作 OAuth 成功，JSON 会单独记录 `authorization_succeeded`。

完整框架的构建命令为 `./gradlew :play-services-core:assembleVtmHuaweiDebug`（在准备好的 GmsCore 目录中）。
这仅生成实验框架，不能当作已可支付的发行包，也不保证能保留现有账号直接更新。

脚本会识别已应用的补丁；遇到其他源码改动或不同的上游提交会停止并保留它们。
本地不需要 Android SDK 的准备流程测试：`python -m unittest discover -s tests -v`。
`native-port-probe/build.py` 使用相邻 `android-sdk/` 构建；运行探针需要单独安装它并提供
Google 签名的、适配设备 Android 版本的原始 APK。它不会替换安装着的 microG。

下一步的实验与验收条件见 [ROADMAP.md](ROADMAP.md)。
