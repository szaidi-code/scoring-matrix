import QtQuick
import Quickshell.Io

// Optional Omarchy shell button. No polling or hardware work until clicked.
Item {
    id: root
    property var settings: ({})
    property var shell
    property var manifest
    property var pluginRegistry
    property string omarchyPath: ""
    implicitWidth: label.implicitWidth + 16
    implicitHeight: 28

    Text {
        id: label
        anchors.centerIn: parent
        text: launcher.running ? "Opening..." : "Score"
        color: mouse.containsMouse ? "#89b4fa" : "#cdd6f4"
        font.pixelSize: 13
        font.bold: true
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: if (!launcher.running) launcher.running = true
    }
    Process {
        id: launcher
        command: ["python3", decodeURIComponent(Qt.resolvedUrl("scoring_matrix.py").toString().replace(/^file:\/\//, "")), "--launch"]
    }
}
