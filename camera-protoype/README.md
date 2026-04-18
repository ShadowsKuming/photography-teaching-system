# Camera Proto

Prototype camera app built with **React**, **Vite**, **TypeScript**, and **Capacitor**. It runs in the browser (web camera) and as a native **iOS** or **Android** app using the device camera APIs.

## Prerequisites

- For **iOS** builds: **Xcode** (macOS only), including the iOS Simulator if you want to run on simulator
- For **Android** builds: **Android Studio** with the Android SDK, platform tools, and a configured emulator or USB debugging for a physical device

## Install dependencies

```bash
npm install
```

## Web (browser)

Start the dev server:

```bash
npm run dev
```

Production build (output in `dist/`):

```bash
npm run build
```

## Native apps (iOS and Android)

Capacitor copies the web build into the native projects. After you change web assets or add Capacitor plugins, sync:

```bash
npm run build
npm run cap sync
```

### iOS (Xcode)

1. Install **Xcode** from the Mac App Store 
2. From the project root:
  ```bash
   npm run build
   npm run cap sync
   npm run cap open ios
  ```
3. In **Xcode**, pick a simulator or a connected iPhone, then use **Product → Run** 

> iOS development requires a **Mac**. You cannot build the iOS app on Windows or Linux.

### Android (Android Studio)

1. Install **Android Studio** and the **Android SDK** (API level matching the project’s `compileSdk 36)`.
2. From the project root:
  ```bash
   npm run build
   npm run cap sync
   npm run cap open android
  ```
3. In **Android Studio**, wait for Gradle sync, choose a device or emulator, then use **Run** (green play button) or **Build → Make Project** to build.

## Useful scripts


| Command                    | Description                                |
| -------------------------- | ------------------------------------------ |
| `npm run dev`              | Vite dev server (web)                      |
| `npm run build`            | Typecheck and production web build         |
| `npm run cap sync`         | Web build + sync to `ios/` and `android/`  |
| `npm run cap open ios`     | Open the iOS project in Xcode              |
| `npm run cap open android` | Open the Android project in Android Studio |


## Project metadata

- **Capacitor app ID:** `com.ufrgs.cameraproto`
- **App name:** Camera Proto

