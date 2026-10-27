# microg-payments-lab

面向华为 Android 兼容系统的 **Google Pay 网页付款兼容性实验工程**。
当前还不能付款，也没有面向普通用户的可安装解决方案。

第一阶段研究 Chrome → microG → Google Pay 在线付款，设备基线是 Pura 70、
HarmonyOS 4.2.0.242 / Android SDK 31。NFC 刷卡和 HarmonyOS NEXT 不属于当前阶段。

## 已有基础

- microG `v0.3.17.252432` 的实验补丁：请求 transaction 17、回调 transaction 12、
  `WebPaymentDataRequest` / `WebPaymentData`，以及 Cart 和 LineItem 的数据模型。
- 独立构造 Wallet SDK 报文的协议测试：保留金额、币种、商品项、未知字段和外层参数；
  检查单向 Binder 调用、错误回调、携带 PendingIntent 的原生界面回调。
- `native-port-probe/`：在独立 Android 应用中测试官方钱包类加载与服务初始化。
  它没有网络或账号权限，不发送付款请求；Google 24.40.34 的实验性上下文适配是版本特定的。
- `research/` 保存本轮公开资料检索结果；`verification/` 保存脱离付款数据的实验结果。

现有服务补丁仍然返回 `API_NOT_CONNECTED`。原生 UI 的 PendingIntent **仅通过协议单元测试**，
没有接入一个能付款的 Activity。一次类加载成功或测试成功都不表示 Google Pay 已可用。

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

在工程根目录准备上游与 Android SDK 后：

```bash
git clone --branch v0.3.17.252432 --depth 1 https://github.com/microg/GmsCore.git GmsCore
git -C GmsCore apply ../patches/0001-wallet-web-protocol-foundation.patch
# 在 GmsCore/local.properties 设置 sdk.dir；需要 Android SDK Platform 35 和 Build Tools 35.0.0。
python tools/lab.py verify --gmscore GmsCore --java-home /usr/lib/jvm/java-17-openjdk
python tools/lab.py status
python tools/lab.py probe-summary verification/native-probe-context-initialized.txt
```

本机已有修改过的 `GmsCore/`，不要重复应用补丁。
`native-port-probe/build.py` 使用相邻 `android-sdk/` 构建；运行探针需要单独安装它并提供
Google 签名的、适配设备 Android 版本的原始 APK。它不会替换安装着的 microG。

下一步的实验与验收条件见 [ROADMAP.md](ROADMAP.md)。
