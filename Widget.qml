import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons

Panel {
  id: root
  moduleName: "szaidi.scoring-matrix"
  ipcTarget: "szaidi.scoring-matrix"
  property var report: null
  property int selected: 0
  property bool showNotes: false
  property string errorMessage: ""
  readonly property string script: decodeURIComponent(Qt.resolvedUrl("scoring_matrix.py").toString().replace(/^file:\/\//, ""))
  readonly property bool busy: scan.running || saved.running
  readonly property var categories: report ? report.Breakdown : []
  readonly property var current: categories.length > selected ? categories[selected] : null
  readonly property var accents: [Color.accent, Color.accent, Color.accent, Color.accent, Color.accent, Color.accent]
  readonly property string targetDisk: String(root.setting("targetDisk", "")).trim()
  readonly property var names: ["CPU", "Memory", "Disk", "Graphics", "Network", "Firmware"]
  readonly property var captions: ["Brain power", "Room to multitask", "Space to build", "Pixel potential", "Stay connected", "Boot readiness"]
  readonly property var rules: [
    "Core capacity earns up to 20 points; thread count adds up to 5. This measures concurrency, not processor speed.",
    "Usable RAM: about 4 / 8 / 16 / 32 / 64 GiB earns 3 / 10 / 18 / 23 / 25 points. Free RAM does not affect your score.",
    "NVMe earns 12, SSD 9, HDD 2. Capacity adds up to 8 points. Only the selected whole disk counts; no disk changes are made.",
    "Intel or AMD earns 12; NVIDIA or hybrid earns 8; other detected graphics earns 3. Three points await functional validation.",
    "Physical Ethernet earns 4; Intel Wi-Fi earns 4, other Wi-Fi 2. Internal controller links are excluded. Two points await functional validation.",
    "UEFI earns 3 points. Confirmed Secure Boot off adds 2. Unknown state earns no off-state points; reported settings keep their provenance."
  ]
  function acceptReport(text) {
    try {
      var value = JSON.parse(text)
      if (value !== null && (!Array.isArray(value.Breakdown) || value.Breakdown.length !== 6 || typeof value.Score !== "number" || !value.Assessment))
        throw new Error("Invalid report")
      root.report = value
      root.errorMessage = ""
    } catch (e) { root.errorMessage = "Could not read the saved score. Try scanning again." }
  }
  function refresh() {
    if (!root.busy) { root.errorMessage = ""; scan.running = true }
  }
  onOpenedChanged: if (opened && !busy) saved.running = true
  Component.onCompleted: saved.running = true
  implicitWidth: trigger.implicitWidth
  implicitHeight: trigger.implicitHeight
  Component.onDestruction: { scan.running = false; saved.running = false }

  WidgetButton {
    id: trigger
    anchors.fill: parent
    bar: root.bar
    text: root.busy ? "Score ···" : "Score" + (root.report ? " " + root.report.Score : "")
    active: root.opened
    tooltipText: root.report ? root.report.Assessment.Title + " · evidence " + root.report.Coverage + "/100" : "Open Scoring Matrix"
    onPressed: function(button) { if (button === Qt.LeftButton) root.toggle() }
  }
  Process {
    id: saved
    command: ["python3", root.script, "--latest-json", "--view-json"]
    stdout: StdioCollector { onStreamFinished: root.acceptReport(text) }
    onExited: function(code, status) { if (code !== 0) root.errorMessage = "Could not load your saved report. Try Rescan." }
  }
  Process {
    id: scan
    command: ["python3", root.script, "--view-json"].concat(root.targetDisk ? ["--target-disk", root.targetDisk] : [])
    stdout: StdioCollector { onStreamFinished: if (text.trim()) root.acceptReport(text) }
    stderr: StdioCollector { onStreamFinished: if (text.trim()) root.errorMessage = text.trim() }
    onExited: function(code, status) { if (code !== 0 && !root.errorMessage) root.errorMessage = "Scan failed. Your previous report is still saved." }
  }

  Timer {
    interval: 10000
    running: saved.running
    onTriggered: { saved.signal(9); root.errorMessage = "Reading saved reports timed out. Your previous score is unchanged." }
  }
  Timer {
    interval: 95000
    running: scan.running
    onTriggered: { scan.signal(9); root.errorMessage = "Scan timed out. Your previous report is still saved." }
  }

  component Label: Text {
    color: Color.popups.text
    font.pixelSize: Style.font.body
    font.family: root.bar ? root.bar.fontFamily : Style.font.family
    textFormat: Text.PlainText
    wrapMode: Text.WordWrap
  }
  component Action: Controls.Button {
    id: action
    implicitHeight: Style.space(34)
    hoverEnabled: true
    contentItem: Label { text: action.text; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; opacity: action.enabled ? 1 : 0.5 }
    background: Rectangle {
      radius: Style.space(8)
      color: Qt.alpha(Color.popups.text, action.hovered ? 0.12 : 0.05)
      border.color: action.activeFocus ? Color.accent : Qt.alpha(Color.popups.text, 0.14)
    }
  }

  KeyboardPanel {
    id: popup
    anchorItem: root
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: content
    contentWidth: popup.fittedContentWidth(Style.space(480))
    contentHeight: popup.fittedContentHeight(contentColumn.implicitHeight, Style.space(840))

    FocusScope {
      id: content
      anchors.fill: parent
      Keys.onEscapePressed: root.close()
      Keys.onLeftPressed: root.selected = (root.selected + 5) % 6
      Keys.onRightPressed: root.selected = (root.selected + 1) % 6
      Keys.onUpPressed: root.selected = (root.selected + 6 - categoryGrid.columns) % 6
      Keys.onDownPressed: root.selected = (root.selected + categoryGrid.columns) % 6
      Keys.onPressed: function(event) {
        if (event.key === Qt.Key_R && event.modifiers === Qt.NoModifier) {
          root.refresh()
          event.accepted = true
        } else if (event.key === Qt.Key_N && event.modifiers === Qt.NoModifier && root.report) {
          root.showNotes = !root.showNotes
          event.accepted = true
        }
      }
      Controls.ScrollView {
        anchors.fill: parent
        contentWidth: availableWidth
        clip: true
        Controls.ScrollBar.horizontal.policy: Controls.ScrollBar.AlwaysOff
        ColumnLayout {
          id: contentColumn
          width: parent.width
          spacing: Style.space(14)
          RowLayout {
            Layout.fillWidth: true
            ColumnLayout {
              Layout.fillWidth: true
              spacing: Style.space(3)
              Label { text: "YOUR MACHINE, DECODED"; font.pixelSize: Style.font.caption; font.letterSpacing: Style.spaceReal(1.5); opacity: 0.6 }
              Label { text: "Scoring Matrix"; font.pixelSize: Style.font.display; font.bold: true }
            }
          }
          Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(Style.space(132), hero.implicitHeight + Style.space(28))
            radius: Style.space(12)
            color: Qt.alpha(Color.accent, 0.07)
            border.color: Qt.alpha(Color.accent, 0.2)
            RowLayout {
              id: hero
              anchors.fill: parent
              anchors.margins: Style.space(14)
              spacing: Style.space(18)
              ScoreRing {
                Layout.preferredWidth: Style.space(104); Layout.preferredHeight: Style.space(104)
                fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                value: root.report ? root.report.Score : 0
                accent: Color.accent; foreground: Color.popups.text; track: Qt.alpha(Color.popups.text, 0.09)
              }
              ColumnLayout {
                Layout.fillWidth: true
                spacing: Style.space(5)
                Label { Layout.fillWidth: true; text: root.report ? root.report.Computer : "Ready when you are"; font.pixelSize: Style.font.heading; font.bold: true }
                Label { Layout.fillWidth: true; text: root.report ? "Resources  " + root.report.Resources + "/70\nCompatibility  " + root.report.Compatibility + "/30" : "Take a local snapshot to discover your score."; lineHeight: 1.25 }
                Label { Layout.fillWidth: true; text: root.busy ? "Taking a look under the hood…" : "Provisional · automatic ceiling 95"; font.pixelSize: Style.font.bodySmall; opacity: 0.65 }
              }
            }
          }
          ColumnLayout {
            Layout.fillWidth: true
            visible: !!root.report
            spacing: Style.space(5)
            Label { Layout.fillWidth: true; font.bold: true; text: root.report ? root.report.Assessment.Title + " · evidence " + root.report.Coverage + "/100" : "" }
            Label { Layout.fillWidth: true; text: root.report ? root.report.Assessment.Detail : ""; font.pixelSize: Style.font.body; opacity: 0.8 }
          }
          Label { text: "PICK A CARD. SEE WHAT COUNTS."; font.pixelSize: Style.font.caption; font.letterSpacing: Style.spaceReal(1); opacity: 0.6; visible: !!root.report }
          GridLayout {
            id: categoryGrid
            Layout.fillWidth: true
            columns: width < Style.space(340) ? 2 : 3
            columnSpacing: Style.space(8)
            rowSpacing: Style.space(8)
            visible: !!root.report
            Repeater {
              model: root.categories
              delegate: Controls.Button {
                id: tile
                required property var modelData
                required property int index
                Layout.fillWidth: true
                Layout.preferredWidth: Style.space(130)
                implicitHeight: Style.space(124)
                hoverEnabled: true
                Accessible.name: root.names[index] + ", " + modelData.Points + " out of " + modelData.Maximum + " points"
                onClicked: { root.selected = index; root.showNotes = false }
                background: Rectangle {
                  radius: Style.space(10)
                  color: Qt.alpha(root.accents[tile.index], root.selected === tile.index ? 0.14 : tile.hovered ? 0.09 : 0.035)
                  border.width: root.selected === tile.index || tile.activeFocus ? 2 : 1
                  border.color: root.selected === tile.index || tile.activeFocus ? root.accents[tile.index] : Qt.alpha(Color.popups.text, 0.12)
                  Behavior on color { ColorAnimation { duration: 120 } }
                }
                contentItem: Column {
                  spacing: Style.space(5)
                  ScoreRing {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Style.space(62); height: Style.space(62); stroke: Style.space(4); numberSize: Style.font.heading
                    fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                    value: tile.modelData.Points; maximum: tile.modelData.Maximum
                    accent: root.accents[tile.index]; foreground: Color.popups.text; track: Qt.alpha(Color.popups.text, 0.08)
                  }
                  Label { anchors.horizontalCenter: parent.horizontalCenter; text: root.names[tile.index]; font.bold: true; font.pixelSize: Style.font.body }
                  Label { anchors.horizontalCenter: parent.horizontalCenter; text: tile.modelData.Known ? "Observed" : "Partial evidence"; font.pixelSize: Style.font.caption; opacity: 0.7 }
                }
              }
            }
          }
          Rectangle {
            Layout.fillWidth: true
            implicitHeight: detail.implicitHeight + Style.space(26)
            visible: !!root.current && !root.showNotes
            radius: Style.space(10)
            color: Qt.alpha(root.accents[root.selected], 0.05)
            border.color: Qt.alpha(root.accents[root.selected], 0.25)
            ColumnLayout {
              id: detail
              anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
              anchors.margins: Style.space(13)
              spacing: Style.space(7)
              RowLayout {
                Layout.fillWidth: true
                Label { Layout.fillWidth: true; text: root.captions[root.selected]; color: root.accents[root.selected]; font.bold: true; font.pixelSize: Style.font.heading }
                Label { text: root.current ? root.current.Points + " / " + root.current.Maximum : ""; font.bold: true }
              }
              Label { Layout.fillWidth: true; text: root.current ? (root.current.Reason || "No hardware detected in this category.") : "" }
              Label { Layout.fillWidth: true; text: root.rules[root.selected]; font.pixelSize: Style.font.body; opacity: 0.7 }
              Label { Layout.fillWidth: true; visible: !!root.current && !root.current.Known; text: "Some data is missing. This category is not fully assessed."; color: Color.urgent; font.pixelSize: Style.font.body }
            }
          }
          Label {
            Layout.fillWidth: true
            visible: root.showNotes && !!root.report
            text: root.report ? root.report.Issues.map(function(note) { return "• " + note }).join("\n\n") : ""
            font.pixelSize: Style.font.body
          }
          Label { Layout.fillWidth: true; visible: root.errorMessage !== ""; text: root.errorMessage; color: Color.urgent; font.pixelSize: Style.font.body }
          RowLayout {
            Layout.fillWidth: true
            Action { Layout.fillWidth: true; text: root.busy ? "Scanning…" : root.report ? "↻  Rescan" : "Discover my score"; enabled: !root.busy; onClicked: root.refresh() }
            Action { Layout.fillWidth: true; text: root.showNotes ? "Back to details" : "Notes & limitations"; enabled: !!root.report; onClicked: root.showNotes = !root.showNotes }
          }
          Label {
            Layout.fillWidth: true
            text: root.report ? "Saved " + new Date(root.report.Captured).toLocaleString(Qt.locale(), "MMM d, h:mm AP") + " · stored only on this computer\nCapacity & compatibility estimate, not a benchmark." : "Local reports only. No uploads."
            font.pixelSize: Style.font.caption
            opacity: 0.55
          }
        }
      }
    }
  }
}
