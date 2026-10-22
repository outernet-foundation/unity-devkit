# unity-devkit

Unity build, license, and CI tooling, plus the `org.outernet.playerbuild` UPM editor package. Agent-facing documentation lives in [`AGENTS.md`](./AGENTS.md).

## Android signing

Every Android player build must be signed with a stable per-app keystore. Without one, Unity signs with the build machine's throwaway debug keystore — every CI runner and dev box produces a differently-signed APK, and Android refuses to install it over the existing app (`INSTALL_FAILED_UPDATE_INCOMPATIBLE`). CI builds take the signing identity from four required workflow secrets; local builds take it from environment variables. The Unity project must consume `org.outernet.playerbuild` 0.3.1 or later — older releases ignore the signing env entirely.

### One-time setup per app

Create a keystore and keep it forever (losing it means one more uninstall-and-reinstall when you adopt its replacement):

```
keytool -genkeypair -keystore myapp.keystore -alias myapp -keyalg RSA -keysize 2048 -validity 36500
```

Set four repository secrets in the consumer repo:

```
base64 < myapp.keystore > myapp.keystore.b64
gh secret set ANDROID_KEYSTORE < myapp.keystore.b64
gh secret set ANDROID_KEYSTORE_PASSWORD
gh secret set ANDROID_KEY_ALIAS
gh secret set ANDROID_KEY_PASSWORD
```

`gh secret set` prompts for each value interactively, so passwords never land in shell history.

Forward them in the consumer's `build-unity` call:

```yaml
    secrets:
      unity-email: ${{ secrets.UNITY_EMAIL }}
      unity-password: ${{ secrets.UNITY_PASSWORD }}
      unity-serial: ${{ secrets.UNITY_SERIAL }}
      android-keystore: ${{ secrets.ANDROID_KEYSTORE }}
      android-keystore-password: ${{ secrets.ANDROID_KEYSTORE_PASSWORD }}
      android-key-alias: ${{ secrets.ANDROID_KEY_ALIAS }}
      android-key-password: ${{ secrets.ANDROID_KEY_PASSWORD }}
```

### Local builds

Export the quartet in the shell that runs `build-unity` / `install --build`:

```
export KEYSTORE_PATH="$HOME/.keystores/myapp.keystore"
export KEYSTORE_PASSWORD=...
export KEYSTORE_ALIAS=myapp
export KEYSTORE_ALIAS_PASSWORD=...
```

All four or none: a partial set fails the build loudly.

### First install after adoption

The build already on the device carries a throwaway signature, so the first correctly-signed install still conflicts — one final `adb uninstall <application-id>`, then updates replace in place forever after.
