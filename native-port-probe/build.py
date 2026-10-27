from pathlib import Path
import subprocess
import os
import zipfile

root = Path(__file__).resolve().parent
sdk = root.parent / "android-sdk"
java = Path("/usr/lib/jvm/java-17-openjdk/bin")
tools = sdk / "build-tools/35.0.0"
android = sdk / "platforms/android-35/android.jar"
out = root / "build"
out.mkdir(exist_ok=True)
(out / "classes").mkdir(exist_ok=True)
env = dict(os.environ, JAVA_HOME=str(java.parent))

def run(args):
    subprocess.run([str(x) for x in args], check=True, env=env)

run([java / "javac", "-source", "8", "-target", "8", "-cp", android,
     "-d", out / "classes", root / "ProbeActivity.java"])
with zipfile.ZipFile(out / "classes.jar", "w") as z:
    for p in (out / "classes").rglob("*.class"):
        z.write(p, str(p.relative_to(out / "classes")))
run([tools / "d8", "--lib", android, "--min-api", "31", "--output", out, out / "classes.jar"])
run([tools / "aapt2", "link", "-I", android, "--manifest", root / "AndroidManifest.xml",
     "-o", out / "unsigned.apk"])
with zipfile.ZipFile(out / "unsigned.apk", "a") as z:
    z.write(out / "classes.dex", "classes.dex")
if not (out / "probe.keystore").exists():
    run([java / "keytool", "-genkeypair", "-keystore", out / "probe.keystore",
         "-storepass", "android", "-keypass", "android", "-alias", "probe",
         "-dname", "CN=WalletCompatibilityProbe", "-keyalg", "RSA", "-keysize", "2048",
         "-validity", "2"])
run([tools / "apksigner", "sign", "--ks", out / "probe.keystore",
     "--ks-pass", "pass:android", "--out", out / "probe.apk", out / "unsigned.apk"])
run([tools / "apksigner", "verify", out / "probe.apk"])
print(out / "probe.apk")
