import QtQuick

Item {
    id: ring
    property real value: 0
    property real maximum: 100
    property color accent: "#89b4fa"
    property color track: "#30343b"
    property color foreground: "white"
    property int stroke: 7
    property int numberSize: 32
    property real progress: Math.max(0, Math.min(1, maximum > 0 ? value / maximum : 0))
    Behavior on progress { NumberAnimation { duration: 550; easing.type: Easing.OutCubic } }
    onProgressChanged: dial.requestPaint()
    onAccentChanged: dial.requestPaint()
    onTrackChanged: dial.requestPaint()
    Canvas {
        id: dial
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        onPaint: {
            var ctx = getContext("2d"); ctx.reset()
            var radius = Math.min(width, height) / 2 - ring.stroke / 2 - 1
            if (radius <= 0) return
            ctx.lineWidth = ring.stroke; ctx.lineCap = "round"
            ctx.strokeStyle = ring.track
            ctx.beginPath(); ctx.arc(width / 2, height / 2, radius, 0, Math.PI * 2); ctx.stroke()
            if (ring.progress > 0) {
                ctx.strokeStyle = ring.accent
                ctx.beginPath(); ctx.arc(width / 2, height / 2, radius, -Math.PI / 2, -Math.PI / 2 + ring.progress * Math.PI * 2); ctx.stroke()
            }
        }
    }
    Column {
        anchors.centerIn: parent
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: ring.value; color: ring.foreground; font.pixelSize: ring.numberSize; font.bold: true }
        Text { anchors.horizontalCenter: parent.horizontalCenter; text: "/ " + ring.maximum; color: ring.foreground; opacity: 0.6; font.pixelSize: 11 }
    }
}
