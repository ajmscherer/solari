# Solari — Native Apple App (iOS / iPadOS / macOS)

This directory will contain the native Swift implementation of the Solari split-flap display for Apple platforms.

## Goals

- Deliver a polished, high-performance native experience on iPhone, iPad, and Mac.
- Reuse the existing Python content pipeline (`InfoFetcher`, `Feeder`, `GlyphSet`, caching, xAI integration) via a Python–Swift bridge when possible.
- Provide buttery-smooth 3D flip animations using SwiftUI + Core Animation.
- Support both the classic Solari aesthetic and modern iOS design patterns (dark mode, haptics, share sheet, widgets, etc.).

## Planned Structure

```
swift/
├── Solari.xcodeproj/
├── Solari/
│   ├── SolariApp.swift
│   ├── ContentView.swift
│   ├── SolariBoardView.swift          // The grid of flipping characters
│   ├── FlipGlyphView.swift            // Core split-flap animation component
│   ├── SolariBoardModel.swift
│   ├── PythonBridge.swift             // Bridge to reuse python/ modules
│   └── Assets.xcassets/
└── Shared/                            // Code shared with macOS target (optional)
```

## Status

This folder is currently a placeholder. The native Swift app will be developed here while the original Python/Kivy desktop app continues to live in the `python/` directory.

## Building

Open `Solari.xcodeproj` in Xcode (once the project is created) and build for iOS Simulator, iOS Device, or macOS.

## Related

- Python desktop app: `../python/`
- Shared resources (font, sound, prompts): `../resources/`
