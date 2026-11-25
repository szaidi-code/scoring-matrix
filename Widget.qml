import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Ui
import qs.Commons
import qs.Commons as Commons

Panel {
  id: root
  moduleName: "szaidi.scoring-matrix"
  ipcTarget: "szaidi.scoring-matrix"
  property var report: null
  property int selected: 0
  property bool showNotes: false
  property string actionMessage: ""
  property var actionCommand: []
  property string advisorTab: "overview"
  property string errorKey: ""
  property string errorDetail: ""
  readonly property string errorMessage: errorDetail !== "" ? errorDetail : (errorKey !== "" ? strings.t(errorKey) : "")
  readonly property string script: decodeURIComponent(Qt.resolvedUrl("scoring_matrix.py").toString().replace(/^file:\/\//, ""))
  readonly property bool busy: scan.running || saved.running || bootReport.running || advisorAction.running
  readonly property var categories: report ? report.Breakdown : []
  readonly property var advice: report && report.Advisor ? report.Advisor : null
  readonly property var current: categories.length > selected ? categories[selected] : null
  readonly property var accents: [Commons.Color.accent, Commons.Color.accent, Commons.Color.accent, Commons.Color.accent, Commons.Color.accent, Commons.Color.accent]
  readonly property string targetDisk: String(root.setting("targetDisk", "")).trim()
  readonly property var categoryKeys: ["cpu", "memory", "disk", "graphics", "network", "firmware"]
  readonly property var formatLocale: Qt.locale(Commons.I18n.formatLocale)
  readonly property var checkNames: ({
    graphics: strings.t("advisor.check.graphics"), wifi: strings.t("advisor.check.wifi"),
    bluetooth: strings.t("advisor.check.bluetooth"), audio: strings.t("advisor.check.audio"),
    suspend: strings.t("advisor.check.suspend"), displays: strings.t("advisor.check.displays")
  })
  readonly property var resultNames: ({
    pass: strings.t("advisor.result.pass"), fail: strings.t("advisor.result.fail"),
    untested: strings.t("advisor.result.untested")
  })

  Commons.Translations {
    id: strings
    directory: Qt.resolvedUrl("i18n")
  }

  function plainText(value, maxLen) {
    var s = String(value === undefined || value === null ? "" : value)
      .replace(/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/g, "")
      .replace(/</g, "\u2039")
      .replace(/>/g, "\u203a")
      .trim()
    var limit = maxLen || 300
    return s.length > limit ? s.slice(0, limit - 1) + "…" : s
  }

  function clearError() {
    root.errorKey = ""
    root.errorDetail = ""
  }

  function setErrorKey(key) {
    root.errorDetail = ""
    root.errorKey = key
  }

  function setStderrError(text) {
    var cleaned = root.plainText(text, 300)
    if (cleaned !== "") {
      root.errorKey = ""
      root.errorDetail = cleaned
    }
  }

  function formatCaptured(isoString) {
    var date = new Date(isoString)
    if (isNaN(date.getTime())) return ""
    return date.toLocaleString(root.formatLocale, strings.t("footer.dateFormat"))
  }

  function acceptReport(text) {
    try {
      var value = JSON.parse(text)
      if (value !== null) {
        if (!Array.isArray(value.Breakdown) || value.Breakdown.length !== 6
            || typeof value.Score !== "number" || !isFinite(value.Score)
            || typeof value.Resources !== "number" || !isFinite(value.Resources)
            || typeof value.Compatibility !== "number" || !isFinite(value.Compatibility)
            || typeof value.Coverage !== "number" || !isFinite(value.Coverage)
            || !value.Assessment || typeof value.Assessment.Title !== "string" || typeof value.Assessment.Detail !== "string"
            || !Array.isArray(value.Issues) || !value.Issues.every(function(note) { return typeof note === "string" }))
          throw new Error("Invalid report")
        for (var i = 0; i < value.Breakdown.length; i++) {
          var part = value.Breakdown[i]
          if (!part || typeof part.Points !== "number" || !isFinite(part.Points)
              || typeof part.Maximum !== "number" || !isFinite(part.Maximum)
              || typeof part.Known !== "boolean" || typeof part.Reason !== "string")
            throw new Error("Invalid report breakdown")
        }
      }
      root.report = value
      root.actionMessage = value && value.Message ? value.Message : ""
      if (value && value.AdvisorError) {
        root.errorKey = ""
        root.errorDetail = root.plainText(value.AdvisorError, 300)
      } else {
        root.clearError()
      }
    } catch (e) { root.setErrorKey("error.readSaved") }
  }

  function refresh() {
    if (!root.busy) { root.clearError(); scan.running = true }
  }
  function runAdvisor(args) {
    if (!root.busy) {
      root.clearError()
      root.actionMessage = ""
      root.actionCommand = ["python3", root.script].concat(args, ["--view-json"])
      advisorAction.running = true
    }
  }
  onOpenedChanged: if (opened && !busy) saved.running = true
  Component.onCompleted: {
    if (root.setting("scanOnStartup", false)) bootReport.running = true
    else saved.running = true
  }
  implicitWidth: trigger.implicitWidth
  implicitHeight: trigger.implicitHeight
  Component.onDestruction: { scan.running = false; saved.running = false; bootReport.running = false; advisorAction.running = false }

  WidgetButton {
    id: trigger
    anchors.fill: parent
    bar: root.bar
    text: root.plainText(
      root.busy
        ? strings.t("bar.scoreBusy")
        : (root.report ? strings.t("bar.scoreValue").arg(Commons.I18n.formatNumber(root.report.Score)) : strings.t("bar.score")),
      64
    )
    active: root.opened
    tooltipText: root.plainText(
      root.report
        ? strings.t("bar.tooltip")
            .arg(root.plainText(root.report.Assessment.Title, 120))
            .arg(Commons.I18n.formatNumber(root.report.Coverage))
            .arg(Commons.I18n.formatNumber(100))
        : strings.t("bar.tooltipIdle"),
      220
    )
    onPressed: function(button) { if (button === Qt.LeftButton) root.toggle() }
  }
  Process {
    id: saved
    command: ["python3", root.script, "--latest-json", "--view-json"]
    stdout: StdioCollector { onStreamFinished: root.acceptReport(text) }
    onExited: function(code, status) { if (code !== 0) root.setErrorKey("error.loadSaved") }
  }
  Process {
    id: advisorAction
    command: root.actionCommand
    stdout: StdioCollector { onStreamFinished: if (text.trim()) root.acceptReport(text) }
    stderr: StdioCollector { onStreamFinished: if (text.trim()) root.setStderrError(text) }
    onExited: function(code, status) { if (code !== 0 && root.errorMessage === "") root.setErrorKey("error.advisorFailed") }
  }
  Process {
    id: scan
    command: ["python3", root.script, "--view-json"].concat(root.targetDisk ? ["--target-disk", root.targetDisk] : [])
    stdout: StdioCollector { onStreamFinished: if (text.trim()) root.acceptReport(text) }
    stderr: StdioCollector { onStreamFinished: if (text.trim()) root.setStderrError(text) }
    onExited: function(code, status) { if (code !== 0 && root.errorMessage === "") root.setErrorKey("error.scanFailed") }
  }

  Process {
    id: bootReport
    command: ["python3", root.script, "--ensure-boot-report", "--view-json"].concat(root.targetDisk ? ["--target-disk", root.targetDisk] : [])
    stdout: StdioCollector { onStreamFinished: if (text.trim()) root.acceptReport(text) }
    stderr: StdioCollector { onStreamFinished: if (text.trim()) root.setStderrError(text) }
    onExited: function(code, status) {
      if (code !== 0 && root.errorMessage === "") root.setErrorKey("error.startupFailed")
    }
  }
  Timer {
    interval: 95000
    running: bootReport.running
    onTriggered: { bootReport.signal(9); root.setErrorKey("error.startupTimeout") }
  }
  Timer {
    interval: 120000
    running: advisorAction.running
    onTriggered: { advisorAction.signal(9); root.setErrorKey("error.advisorTimeout") }
  }

  Timer {
    interval: 10000
    running: saved.running
    onTriggered: { saved.signal(9); root.setErrorKey("error.savedTimeout") }
  }
  Timer {
    interval: 95000
    running: scan.running
    onTriggered: { scan.signal(9); root.setErrorKey("error.scanTimeout") }
  }

  component Label: Text {
    color: Commons.Color.popups.text
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
      color: Qt.alpha(Commons.Color.popups.text, action.hovered ? 0.12 : 0.05)
      border.color: action.activeFocus ? Commons.Color.accent : Qt.alpha(Commons.Color.popups.text, 0.14)
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
      Keys.onUpPressed: root.selected = (root.selected + 6 - categoryGrid.columns) % 6
      Keys.onDownPressed: root.selected = (root.selected + categoryGrid.columns) % 6
      Keys.onPressed: function(event) {
        var reading = Commons.Util.readingKey(event)
        if (reading === Qt.Key_Left) {
          root.selected = (root.selected + 5) % 6
          event.accepted = true
        } else if (reading === Qt.Key_Right) {
          root.selected = (root.selected + 1) % 6
          event.accepted = true
        } else if (event.key === Qt.Key_R && event.modifiers === Qt.NoModifier) {
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
              Label { text: strings.t("panel.eyebrow"); font.pixelSize: Style.font.caption; font.letterSpacing: Style.spaceReal(1.5); opacity: 0.6 }
              Label { text: strings.t("panel.title"); font.pixelSize: Style.font.display; font.bold: true }
            }
          }
          Rectangle {
            Layout.fillWidth: true
            implicitHeight: Math.max(Style.space(132), hero.implicitHeight + Style.space(28))
            radius: Style.space(12)
            color: Qt.alpha(Commons.Color.accent, 0.07)
            border.color: Qt.alpha(Commons.Color.accent, 0.2)
            RowLayout {
              id: hero
              anchors.fill: parent
              anchors.margins: Style.space(14)
              spacing: Style.space(18)
              ScoreRing {
                Layout.preferredWidth: Style.space(104); Layout.preferredHeight: Style.space(104)
                fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                value: root.report ? root.report.Score : 0
                maximumText: strings.t("ring.maximum").arg(Commons.I18n.formatNumber(100))
                accent: Commons.Color.accent; foreground: Commons.Color.popups.text; track: Qt.alpha(Commons.Color.popups.text, 0.09)
              }
              ColumnLayout {
                Layout.fillWidth: true
                spacing: Style.space(5)
                Label { Layout.fillWidth: true; text: root.report ? strings.t("hero.computer") : strings.t("hero.ready"); font.pixelSize: Style.font.heading; font.bold: true }
                Label {
                  Layout.fillWidth: true
                  text: root.report
                    ? strings.t("hero.subtotals")
                        .arg(Commons.I18n.formatNumber(root.report.Resources))
                        .arg(Commons.I18n.formatNumber(70))
                        .arg(Commons.I18n.formatNumber(root.report.Compatibility))
                        .arg(Commons.I18n.formatNumber(30))
                        .arg(Commons.I18n.formatNumber(root.report.Coverage))
                        .arg(Commons.I18n.formatNumber(100))
                    : strings.t("hero.emptyPrompt")
                  lineHeight: 1.25
                }
                Label {
                  Layout.fillWidth: true
                  text: root.busy ? strings.t("hero.scanning") : strings.t("hero.provisional").arg(Commons.I18n.formatNumber(95))
                  font.pixelSize: Style.font.bodySmall
                  opacity: 0.65
                }
              }
            }
          }
          ColumnLayout {
            Layout.fillWidth: true
            visible: !!root.report
            spacing: Style.space(5)
            Label {
              Layout.fillWidth: true
              font.bold: true
              text: root.report
                ? strings.t("assessment.summary")
                    .arg(root.report.Assessment.Title)
                    .arg(Commons.I18n.formatNumber(root.report.Coverage))
                    .arg(Commons.I18n.formatNumber(100))
                : ""
            }
            Label { Layout.fillWidth: true; text: root.report ? root.report.Assessment.Detail : ""; font.pixelSize: Style.font.body; opacity: 0.8 }
          }
          RowLayout {
            Layout.fillWidth: true
            visible: !!root.advice
            Repeater {
              model: [{key: "overview", label: strings.t("advisor.tab.advice")}, {key: "checks", label: strings.t("advisor.tab.checks")}, {key: "history", label: strings.t("advisor.tab.history")}]
              delegate: Action {
                required property var modelData
                Layout.fillWidth: true
                text: modelData.label
                opacity: root.advisorTab === modelData.key ? 1 : 0.65
                onClicked: root.advisorTab = modelData.key
              }
            }
          }
          ColumnLayout {
            Layout.fillWidth: true
            visible: !!root.advice && root.advisorTab === "overview"
            spacing: Style.space(7)
            Label { text: strings.t("advisor.nextSteps"); font.bold: true; color: Commons.Color.accent }
            Repeater {
              model: root.advice ? root.advice.Recommendations : []
              Label { required property var modelData; Layout.fillWidth: true; text: "• " + modelData }
            }
            Label { text: strings.t("advisor.workload"); font.bold: true; color: Commons.Color.accent }
            Flow {
              Layout.fillWidth: true
              spacing: Style.space(6)
              Repeater {
                model: [{key: "everyday", label: strings.t("advisor.profile.everyday")}, {key: "development", label: strings.t("advisor.profile.development")}, {key: "containers", label: strings.t("advisor.profile.containers")}, {key: "gaming-ai", label: strings.t("advisor.profile.gamingAi")}]
                delegate: Action {
                  required property var modelData
                  text: modelData.label + (root.advice && root.advice.Profile === modelData.key ? " ✓" : "")
                  enabled: !root.busy
                  onClicked: root.runAdvisor(["--profile", modelData.key])
                }
              }
            }
            Label { Layout.fillWidth: true; text: root.advice ? root.advice.ProfileGuidance : ""; opacity: 0.8 }
            Label { Layout.fillWidth: true; text: strings.t("advisor.profileNote"); font.pixelSize: Style.font.caption; opacity: 0.65 }
          }
          ColumnLayout {
            Layout.fillWidth: true
            visible: !!root.advice && root.advisorTab === "checks"
            spacing: Style.space(8)
            Label { Layout.fillWidth: true; text: strings.t("advisor.checksTitle"); font.bold: true; color: Commons.Color.accent }
            Label { Layout.fillWidth: true; text: strings.t("advisor.checksNote"); opacity: 0.8 }
            Repeater {
              model: root.advice ? root.advice.Checks : []
              delegate: ColumnLayout {
                id: checkRow
                required property var modelData
                Layout.fillWidth: true
                Label {
                  Layout.fillWidth: true
                  text: root.checkNames[modelData.Key] + " · " + (modelData.Stale ? strings.t("advisor.retest") : root.resultNames[modelData.Result]) +
                        (modelData.Captured ? " · " + root.formatCaptured(modelData.Captured) : "")
                }
                Label {
                  Layout.fillWidth: true
                  visible: !!modelData.Environment
                  text: modelData.Environment || ""
                  font.pixelSize: Style.font.caption
                  opacity: 0.65
                }
                RowLayout {
                  Layout.fillWidth: true
                  Repeater {
                    model: [{key: "pass", label: strings.t("advisor.result.pass")}, {key: "fail", label: strings.t("advisor.result.fail")}, {key: "untested", label: strings.t("advisor.result.untested")}]
                    delegate: Action {
                      required property var modelData
                      Layout.fillWidth: true
                      text: modelData.label
                      enabled: !root.busy
                      onClicked: root.runAdvisor(["--set-check", checkRow.modelData.Key, modelData.key])
                    }
                  }
                }
              }
            }
          }
          ColumnLayout {
            Layout.fillWidth: true
            visible: !!root.advice && root.advisorTab === "history"
            spacing: Style.space(8)
            Label { text: strings.t("advisor.historyTitle"); font.bold: true; color: Commons.Color.accent }
            Label { Layout.fillWidth: true; text: root.advice && root.advice.PreviousCaptured ? strings.t("advisor.comparedWith").arg(root.formatCaptured(root.advice.PreviousCaptured)) : strings.t("advisor.noHistory") }
            Repeater {
              model: root.advice ? root.advice.Changes : []
              Label { required property var modelData; Layout.fillWidth: true; text: "• " + modelData }
            }
            Label { text: strings.t("advisor.benchmarkTitle"); font.bold: true; color: Commons.Color.accent }
            Label {
              Layout.fillWidth: true
              text: root.advice && root.advice.Benchmark ? strings.t("advisor.benchmarkResult")
                    .arg(root.advice.Benchmark.MedianSeconds.toLocaleString(root.formatLocale, 'f', 3))
                    .arg(root.formatCaptured(root.advice.Benchmark.Captured)) +
                    (root.advice.Benchmark.Stale ? strings.t("advisor.systemChanged") : "") : strings.t("advisor.notRun")
            }
            Label { Layout.fillWidth: true; text: strings.t("advisor.benchmarkNote"); font.pixelSize: Style.font.caption; opacity: 0.75 }
            Action { Layout.fillWidth: true; text: strings.t("advisor.runBenchmark"); enabled: !root.busy; onClicked: root.runAdvisor(["--benchmark-cpu"]) }
            Label { text: strings.t("advisor.exportTitle"); font.bold: true; color: Commons.Color.accent }
            Label { Layout.fillWidth: true; text: strings.t("advisor.exportNote"); font.pixelSize: Style.font.caption; opacity: 0.75 }
            Action { Layout.fillWidth: true; text: strings.t("advisor.export"); enabled: !root.busy; onClicked: root.runAdvisor(["--export-redacted"]) }
          }
          Label { text: strings.t("grid.prompt"); font.pixelSize: Style.font.caption; font.letterSpacing: Style.spaceReal(1); opacity: 0.6; visible: !!root.report }
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
                Accessible.name: strings.t("category.accessible")
                  .arg(strings.t("category." + root.categoryKeys[index] + ".name"))
                  .arg(Commons.I18n.formatNumber(modelData.Points))
                  .arg(Commons.I18n.formatNumber(modelData.Maximum))
                onClicked: { root.selected = index; root.showNotes = false }
                background: Rectangle {
                  radius: Style.space(10)
                  color: Qt.alpha(root.accents[tile.index], root.selected === tile.index ? 0.14 : tile.hovered ? 0.09 : 0.035)
                  border.width: root.selected === tile.index || tile.activeFocus ? 2 : 1
                  border.color: root.selected === tile.index || tile.activeFocus ? root.accents[tile.index] : Qt.alpha(Commons.Color.popups.text, 0.12)
                  Behavior on color { ColorAnimation { duration: Style.duration(120); easing.type: Easing.OutCubic } }
                }
                contentItem: Column {
                  spacing: Style.space(5)
                  ScoreRing {
                    anchors.horizontalCenter: parent.horizontalCenter
                    width: Style.space(62); height: Style.space(62); stroke: Style.space(4); numberSize: Style.font.heading
                    fontFamily: root.bar ? root.bar.fontFamily : Style.font.family
                    value: tile.modelData.Points; maximum: tile.modelData.Maximum
                    maximumText: strings.t("ring.maximum").arg(Commons.I18n.formatNumber(tile.modelData.Maximum))
                    accent: root.accents[tile.index]; foreground: Commons.Color.popups.text; track: Qt.alpha(Commons.Color.popups.text, 0.08)
                  }
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: strings.t("category." + root.categoryKeys[tile.index] + ".name")
                    font.bold: true
                    font.pixelSize: Style.font.body
                  }
                  Label {
                    anchors.horizontalCenter: parent.horizontalCenter
                    text: tile.modelData.Known ? strings.t("category.observed") : strings.t("category.partialEvidence")
                    font.pixelSize: Style.font.caption
                    opacity: 0.7
                  }
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
                Label {
                  Layout.fillWidth: true
                  text: strings.t("category." + root.categoryKeys[root.selected] + ".caption")
                  color: root.accents[root.selected]
                  font.bold: true
                  font.pixelSize: Style.font.heading
                }
                Label {
                  text: root.current
                    ? strings.t("detail.points")
                        .arg(Commons.I18n.formatNumber(root.current.Points))
                        .arg(Commons.I18n.formatNumber(root.current.Maximum))
                    : ""
                  font.bold: true
                }
              }
              Label {
                Layout.fillWidth: true
                text: root.current ? (root.current.Reason || strings.t("detail.noneDetected")) : ""
              }
              Label {
                Layout.fillWidth: true
                text: strings.t("category." + root.categoryKeys[root.selected] + ".rule")
                font.pixelSize: Style.font.body
                opacity: 0.7
              }
              Label {
                Layout.fillWidth: true
                visible: !!root.current && !root.current.Known
                text: strings.t("detail.missingEvidence")
                color: Commons.Color.urgent
                font.pixelSize: Style.font.body
              }
            }
          }
          Label {
            Layout.fillWidth: true
            visible: root.showNotes && !!root.report
            text: root.report ? root.report.Issues.map(function(note) { return "• " + note }).join("\n\n") : ""
            font.pixelSize: Style.font.body
          }
          Label { Layout.fillWidth: true; visible: root.errorMessage !== ""; text: root.errorMessage; color: Commons.Color.urgent; font.pixelSize: Style.font.body }
          Label { Layout.fillWidth: true; visible: root.actionMessage !== ""; text: root.actionMessage; color: Commons.Color.accent; font.pixelSize: Style.font.body }
          RowLayout {
            Layout.fillWidth: true
            Action {
              Layout.fillWidth: true
              text: root.busy ? strings.t("action.scanning") : (root.report ? strings.t("action.rescan") : strings.t("action.discover"))
              enabled: !root.busy
              onClicked: root.refresh()
            }
            Action {
              Layout.fillWidth: true
              text: root.showNotes ? strings.t("action.backToDetails") : strings.t("action.notes")
              enabled: !!root.report
              onClicked: root.showNotes = !root.showNotes
            }
          }
          Label {
            Layout.fillWidth: true
            text: root.report ? strings.t("footer.saved").arg(root.formatCaptured(root.report.Captured)) : strings.t("footer.localOnly")
            font.pixelSize: Style.font.caption
            opacity: 0.55
          }
        }
      }
    }
  }
}
