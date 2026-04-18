# solari


## A simple Python program that emulates the old Solari panels which were place in airports and other public places to provide information such as flight departures and arrivals

<p align="center">
	<img src="resources/images/Airport%20hall.jpg" alt="Airport hall" height="300">
	&nbsp;&nbsp;&nbsp;&nbsp;
	<img src="resources/images/Panel%20closeup.jpg" alt="Panel closeup" height="300">
</p>

A demo youtube video is available below.

## Features

## Quick start

### prepare environment

[create environment - install dependendcies]
[rename and configure .env.example with user's API keys]

### run solari

## Program structure

### Layered architecture

```mermaid
flowchart TB
  subgraph Runtime[Runtime Entry]
    Run[solari_run.py]
  end

  subgraph UI[UI Layer]
    GI[GraphicInterface]
    KGI[KiviGraphicInterface]
    GA[GraphicApp]
    SA[SolariApp]
    Canvas[Canvas / CanvasWrapperKivy / CanvasRelative]
  end

  subgraph Feed[Feed Layer]
    F[Feeder]
    FS[FeederStatic]
    FI[FeederInfo]
    FM[FeederMix]
    Msg[Message]
  end

  subgraph Fetch[Fetch Layer]
    IF[InfoFetcher]
    NF[NewsFetcher]
    XA[InfoFetcher_xAI]
    IS[InfoSource]
    Sch[Scheduler]
    VR[ValueRotation]
  end

  subgraph Display[Display Model]
    GS[GlyphSet]
    GP[GlyphPanel]
    GPort[GlyphPort x N]
    Glyph[Glyph / CharGlyph]
    GR[GlyphRanker]
  end

  Run --> KGI
  Run --> FM
  Run --> SA
  KGI -.implements .-> GI
  SA -.extends .-> GA
  SA --> KGI
  SA --> FM
  SA --> GS
  SA --> GP
  GP --> GPort
  GP --> GS
  GP --> GR
  GPort --> Glyph
  FM --> F
  FI -.extends .-> F
  FS -.extends .-> F
  FM -.extends .-> F
  FI --> IF
  IF -.extends .-> NF
  IF -.extends .-> XA
  IF --> IS
  IF --> Sch
  IF --> VR
  F --> Msg
  IF --> Msg
  SA --> Canvas
```

### Inheritance tree

```mermaid
classDiagram
  class GraphicInterface
  class KiviGraphicInterface
  GraphicInterface <|-- KiviGraphicInterface

  class Canvas
  class CanvasRelative
  class CanvasWrapperKivy
  Canvas <|-- CanvasRelative
  Canvas <|-- CanvasWrapperKivy

  class GraphicApp
  class SolariApp
  GraphicApp <|-- SolariApp

  class Feeder
  class FeederStatic
  class FeederInfo
  class FeederMix
  Feeder <|-- FeederStatic
  Feeder <|-- FeederInfo
  Feeder <|-- FeederMix

  class InfoFetcher
  class NewsFetcher
  class InfoFetcher_xAI
  InfoFetcher <|-- NewsFetcher
  InfoFetcher <|-- InfoFetcher_xAI

  class myobject
  class Glyph
  class CharGlyph
  myobject <|-- Glyph
  Glyph <|-- CharGlyph
```

## How it works 

### the vizualation logic

### the news gathering logic

### News item to animated panel sequence

```mermaid
sequenceDiagram
  participant Runner as solari_run.py
  participant App as SolariApp
  participant Feeder as FeederMix/FeederInfo
  participant Fetcher as InfoFetcher
  participant Rotation as ValueRotation
  participant Message as Message
  participant Panel as GlyphPanel
  participant Port as GlyphPort[*]
  participant UI as KiviGraphicInterface

  Runner->>Fetcher: start()
  Fetcher->>Fetcher: fetch()
  Fetcher->>Rotation: mostRecentInfo()

  Runner->>App: construct(graphicInterface, feeder)
  Runner->>App: run()
  App->>UI: start(drawMainWindow)

  loop refresh cycle
    App->>Feeder: getMessage()
    Feeder->>Fetcher: next() / record lookup
    Fetcher->>Rotation: next()
    Rotation-->>Fetcher: record
    Fetcher->>Message: recordAsSolariMessage(record, panelSize)
    Message-->>Feeder: formatted message
    Feeder-->>App: Message
    App->>Panel: updateText(message.text)
    Panel->>Port: setNewTargetGlyph(...) for each cell
    UI->>App: draw(canvas, time)
    App->>Panel: draw(canvas, time)
    Panel->>Port: draw(canvasRelative, time)
  end
```


## Demo


  <a href="https://youtu.be/Kv-tkJvaFZI">
    <p align="center">
    <img src="/Users/alex/Documents/CODE/PUBLISHED/solari/resources/images/Screenshot Solari.png" alt="Watch the demo" height="300">
    </p>
  </a>

## License
This project is licensed under the GNU Affero General Public License v3.0 (AGPLv3) for open-source and non-commercial use.
For commercial use, closed-source integration, SaaS deployment, or enterprise licensing, please contact me.

## Editing credits
Grok and Microsoft Copilote assisted Alex Scherer in editing this readme file, most significantly by proposing verbiage for the sections analyzing how the code works and proposing grammar and stylistic corrections. 

## Disclaimer
This tool is presented "as is", for educational and informational purposes only. It is not financial advice. Always consult a qualified financial advisor for actual investment decisions.
