import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Material 2.12

import QtQuick.Layouts 1.3
import QtQuick.Window 2.12


import Qt.labs.qmlmodels 1.0

ApplicationWindow{
    title: "Parameter Viewer"
    width: 450
    height: 1050
    visible: true
    Material.theme: Material.Light

    TabBar {
        id : param_viewer
        height: 40
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.top: parent.top
        anchors.topMargin: 0

        TabButton {
            text: qsTr("Gates")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }

        TabButton {
            text: qsTr("Virtual Gates")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }
    }

    StackLayout {
        id: stackLayout
        currentIndex: param_viewer.currentIndex
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.top: param_viewer.bottom

        Item {
            id: awg_dac_ratio_tab
        }
    }
}