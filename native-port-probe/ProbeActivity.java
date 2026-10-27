package org.local.walletcompatprobe;

import android.app.Activity;
import android.content.Context;
import android.content.ContextWrapper;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.os.Bundle;
import android.util.Log;
import android.widget.TextView;
import dalvik.system.DexClassLoader;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.charset.StandardCharsets;

/** An isolated linkage probe: no account, network or payment permissions. */
public final class ProbeActivity extends Activity {
    private static final String TAG = "WalletCompatProbe";
    private TextView output;
    private final StringBuilder lines = new StringBuilder();

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        output = new TextView(this);
        output.setPadding(24, 24, 24, 24);
        setContentView(output);
        new Thread(this::probe, "wallet-linkage-probe").start();
    }

    private synchronized void line(String value) {
        Log.e(TAG, value);
        try (FileOutputStream file = new FileOutputStream(new File(getFilesDir(), "result.txt"), true)) {
            file.write((value + "\n").getBytes(StandardCharsets.UTF_8));
        } catch (Exception ignored) {}
        lines.append(value).append('\n');
        String text = lines.toString();
        runOnUiThread(() -> output.setText(text));
    }

    private void probe() {
        File apk = new File(getExternalFilesDir("probe"), "gms.apk");
        if (!apk.isFile()) {
            line("WAITING_FOR_APK " + apk.getAbsolutePath());
            return;
        }
        line("HOST sdk=" + android.os.Build.VERSION.SDK_INT + "; isolated package; no permissions");
        try {
            PackageInfo info = getPackageManager().getPackageArchiveInfo(apk.getAbsolutePath(), 0);
            if (info == null) throw new IllegalArgumentException("APK could not be parsed");
            line("PAYLOAD version=" + info.versionName + " minSdk=" + info.applicationInfo.minSdkVersion);
            if (info.applicationInfo.minSdkVersion > android.os.Build.VERSION.SDK_INT) {
                line("SKIPPED incompatible Android version");
                return;
            }
            DexClassLoader loader = new DexClassLoader(apk.getAbsolutePath(),
                    getCodeCacheDir().getAbsolutePath(), apk.getAbsolutePath() + "!/lib/arm64-v8a", getClassLoader());
            // Version-specific experiment identified in Google's 24.40.34 binary:
            // amex is the BaseApplicationContext singleton required before the
            // Chimera service constructor initializes ModuleManager.
            if (getIntent().getBooleanExtra("initializeNativeContext", false)) {
                try {
                    Object base = Class.forName("amex", true, loader).getDeclaredConstructor().newInstance();
                    java.lang.reflect.Method attach = ContextWrapper.class.getDeclaredMethod("attachBaseContext", Context.class);
                    attach.setAccessible(true);
                    attach.invoke(base, getApplicationContext());
                    line("BASE_CONTEXT_OK Google singleton initialized with isolated host context");
                } catch (Throwable failure) {
                    failure("BASE_CONTEXT_FAIL", "amex", failure);
                }
            }
            String[] names = {
                "com.google.android.gms.wallet.WebPaymentDataRequest",
                "com.google.android.gms.wallet.service.PaymentChimeraService",
                "com.google.android.gms.wallet.ib.IbChimeraActivity",
                "com.google.android.gms.wallet.ow.RootChimeraActivity",
                "com.google.android.gms.wallet.bender3.impl.GenericDelegatorChimeraActivityX"
            };
            for (String name : names) {
                try {
                    Class<?> type = Class.forName(name, false, loader);
                    line("LINK_OK " + name + " parent=" + type.getSuperclass().getName());
                    if (name.endsWith("PaymentChimeraService")) {
                        try {
                            Object service = type.getDeclaredConstructor().newInstance();
                            line("CONSTRUCT_OK " + service.getClass().getName());
                            try {
                                java.lang.reflect.Method attach = ContextWrapper.class.getDeclaredMethod("attachBaseContext", Context.class);
                                attach.setAccessible(true);
                                attach.invoke(service, this);
                                type.getMethod("onCreate").invoke(service);
                                line("CREATE_OK " + name);
                                Object binder = type.getMethod("onBind", Intent.class).invoke(service,
                                        new Intent("com.google.android.gms.wallet.service.BIND"));
                                line("BIND_RESULT " + (binder == null ? "null" : binder.getClass().getName()));
                            } catch (Throwable failure) {
                                failure("SERVICE_INIT_FAIL", name, failure);
                            }
                        } catch (Throwable failure) {
                            failure("CONSTRUCT_FAIL", name, failure);
                        }
                    }
                } catch (Throwable failure) {
                    failure("LINK_FAIL", name, failure);
                }
            }
        } catch (Throwable failure) {
            failure("LOADER_FAIL", "DexClassLoader", failure);
        }
        line("PROBE_DONE; no account access, wallet requests or payment performed");
    }

    private void failure(String stage, String name, Throwable failure) {
        line(stage + " " + name);
        for (int depth = 0; failure != null && depth < 5; depth++) {
            line("CAUSE " + failure.getClass().getName() + ": " + failure.getMessage());
            StackTraceElement[] frames = failure.getStackTrace();
            for (int i = 0; i < Math.min(4, frames.length); i++) line(" AT " + frames[i]);
            failure = failure.getCause();
        }
    }
}
