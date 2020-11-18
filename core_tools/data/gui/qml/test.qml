import QtQuick 2.4
import QtGraphicalEffects 1.0
import QtQuick.Controls 1.6
import QtQuick.Dialogs.qml 1.0
import QtQuick.Controls.Styles.Desktop 1.0
import QtQuick.Layouts 1.3
import QtQuick.Window 2.10

import QtQuick.Layouts 1.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Styles 1.4
import QtQuick.Window 2.12
import QtQuick.Controls.Material 2.12

Page {
    id: page
    width: 1500
    height: 800
    visible: true


    TabBar {
        id: tabBar
        height: 50
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.top: parent.top
        anchors.topMargin: 0

        TabButton {
            id: tabButton
            text: qsTr("Overview")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }

        TabButton {
            id: tabButton1
            text: qsTr("Search")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }
    }

    StackLayout {
        id: stackLayout
        anchors.bottomMargin: 50
        currentIndex: tabBar.currentIndex
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.bottom: parent.bottom
        anchors.top: tabBar.bottom
        anchors.topMargin: 0

        Item {
            id: element6

            ColumnLayout{
                id: rowLayout
                anchors.fill: parent
                transformOrigin: Item.TopLeft
                spacing: 10

                RowLayout {
                    id: columnLayout
                    x: 0
                    y: 0
                    width: 0
                    height: 0
                    Layout.margins: 5
                    Layout.fillHeight: false
                    Layout.maximumHeight: 65535
                    transformOrigin: Item.TopLeft
                    Layout.minimumWidth: 0
                    Layout.fillWidth: true


                    RowLayout {
                        id: rowLayout1
                        width: 100
                        height: 100
                        Layout.minimumWidth: 0
                        Layout.fillHeight: false
                        Layout.fillWidth: false

                        Text {
                            id: element
                            width: 80
                            height: 40
                            text: qsTr("Project")
                            Layout.preferredWidth: 80
                            Layout.bottomMargin: 0
                            lineHeight: 1
                            fontSizeMode: Text.FixedSize
                            font.pixelSize: 20
                        }

                        ComboBox {
                            id: comboBox
                            model: ["First", "Second", "Third"]
                            Layout.preferredWidth: 250
                            Layout.margins: 5
                        }
                    }

                    Item {
                        id: element4
                        width: 0
                        height: 0
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        id: rowLayout2
                        width: 100
                        height: 100


                        Text {
                            id: element2
                            width: 80
                            height: 40
                            text: qsTr("Sample")
                            Layout.preferredWidth: 80
                            font.pixelSize: 20
                        }
                        ComboBox {
                            id: comboBox2
                            model: ["First", "Second", "Third"]
                            Layout.preferredWidth: 250
                            Layout.margins: 5
                        }
                    }

                    Item {
                        id: element3
                        Layout.fillHeight: false
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        id: rowLayout3
                        width: 100
                        height: 100

                        Text {
                            id: element1
                            height: 40
                            text: qsTr("Set up")
                            Layout.preferredWidth: 80
                            font.pixelSize: 20
                        }

                        ComboBox {
                            id: comboBox1
                            model: ["First", "Second", "Third"]
                            Layout.preferredWidth: 250
                            Layout.margins: 5
                        }
                    }
                    Item {
                        id: element5
                        Layout.minimumWidth: 0
                        Layout.fillHeight: false
                        Layout.fillWidth: true
                    }
                }

                RowLayout {
                    id: columnLayout1
                    width: 0
                    height: 0

                    ListView {
                        id: listView
                        width: 202
                        height: 344
                        Layout.leftMargin: 8
                        smooth: true
                        clip: false
                        visible: true
                        opacity: 1
                        layoutDirection: Qt.LeftToRight
                        snapMode: ListView.SnapToItem
                        spacing: 2
                        cacheBuffer: 200
                        boundsBehavior: Flickable.StopAtBounds
                        Layout.bottomMargin: 8
                        Layout.topMargin: 0
                        Layout.maximumWidth: 200
                        Layout.minimumWidth: 200
                        z: 0
                        Layout.fillHeight: true
                        Layout.fillWidth: false
                        delegate: Item {
                            x: 5
                            width: 80
                            height: 40
                            Row {
                                id: row1
                                spacing: 10
                                Rectangle {
                                    width: 40
                                    height: 40
                                    color: colorCode
                                }

                                Text {
                                    text: name
                                    font.bold: true
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }
                        }
                        model: ListModel {
                            ListElement {
                                name: "27/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "25/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "24/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "23/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "22/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "21/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                            ListElement {
                                name: "20/12/2020"
                                colorCode: "grey"
                            }
                        }
                    }

                    TableView {
                        id: tableView
                        width: 580
                        height: 344
                        Layout.bottomMargin: 8
                        Layout.rightMargin: 8
                        transformOrigin: Item.Center
                        sortIndicatorVisible: true
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                    }
                }

            }
        }

        Item {
            id: element7
            Layout.fillHeight: true
            Layout.fillWidth: true

            TextField {
                id: textField
                height: 80
                anchors.right: parent.right
                anchors.rightMargin: 10
                anchors.left: parent.left
                anchors.leftMargin: 10
                anchors.top: parent.top
                anchors.topMargin: 10
                font.pointSize: 20
                placeholderText: qsTr("P1, P2 FROM 12/10/2020 SORT DATE")
            }

            TableView {
                id: tableView1
                anchors.right: parent.right
                anchors.rightMargin: 8
                anchors.left: parent.left
                anchors.leftMargin: 8
                anchors.bottom: parent.bottom
                anchors.bottomMargin: 8
                anchors.top: textField.bottom
                anchors.topMargin: 8
            }
        }
    }

    RowLayout {
        id: rowLayout4
        height: 50
        spacing: 0
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 0
        anchors.top: stackLayout.bottom
        anchors.topMargin: 0

        Rectangle {
            id: rectangle
            width: 250
            height: 50
            color : "transparent"
            Layout.preferredWidth: 250

            RadioButton {
                Material.accent: Material.Teal
                id: radioDelegate
                x: 0
                y: 0
                width: 250
                height: 50
                text: qsTr(" Local Connection")
                leftPadding: 15
                padding: 0
                checkable: false
                display: AbstractButton.TextBesideIcon
                checked: true
            }
        }

        Rectangle {
            id: rectangle1
            width: 250
            height: 50
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.preferredWidth: 250
            color : "transparent"

            RadioButton {
                Material.accent: Material.Red
                id: radioDelegate1
                width: 250
                height: 50
                text: qsTr(" Remote Connecetion")
                leftPadding: 15
                padding: 0
                checkable: false
                checked: true
            }
        }

        Item {
            id: element8
            width: 200
            height: 50
            Layout.preferredHeight: 50
            Layout.fillWidth: true
        }

        SwitchDelegate {
            id: switchDelegate
            width: 250
            height: 50
            text: qsTr("Enable liveplotting")
            Layout.preferredWidth: 250
            checked: true
        }
    }


}

/*##^##
Designer {
    D{i:1;anchors_height:0;anchors_width:0;anchors_x:0;anchors_y:0}D{i:6;anchors_height:0;anchors_width:0;anchors_x:0;anchors_y:0}
D{i:43;anchors_height:635;anchors_width:1479;anchors_x:8;anchors_y:52}D{i:4;anchors_height:50;anchors_width:0;anchors_x:0;anchors_y:0}
D{i:44;anchors_height:100;anchors_width:100}
}
##^##*/
