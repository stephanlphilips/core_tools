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
import QtQuick.Shapes 1.12

ApplicationWindow{
	title: "Data Browser"
	width: 1600
    height: 800
    visible: true
    Material.theme: Material.Light

    Rectangle{
        id:row_overview
        width : 800
        height : 400
    
        Item{
            width: 200
            height: 42
            TextInput {
                id: textField
                height: 42
                Layout.preferredWidth: 300
                font.pixelSize: 16
                text : 'namedfmnslkfj'
                focus : true
            }
        }

        Item{
            y  :50
            width: 200
            height: 42
            TextInput {
                id: textField2
                height: 42
                Layout.preferredWidth: 300
                font.pixelSize: 16
                text : 'namedfmnslkfj'
                focus : true
                z: 3
            }
        }

        MouseArea {
            anchors.fill: parent
            hoverEnabled: true
            propagateComposedEvents: true
            onEntered: row_overview.color= "#EEEEEE"
            onExited: row_overview.color= "#F5F5F5"
            onDoubleClicked : console.log('double_click')
            z: -1
            // onClicked: mouse.accepted = false;
            // onPressed: mouse.accepted = true;
            // onReleased: mouse.accepted = false;
            // onPositionChanged: mouse.accepted = false;
            // onPressAndHold: mouse.accepted = false;
        }
    }
}