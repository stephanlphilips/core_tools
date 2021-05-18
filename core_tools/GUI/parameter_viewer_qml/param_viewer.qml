import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Material 2.12

import QtQuick.Layouts 1.3
import QtQuick.Window 2.12


import Qt.labs.qmlmodels 1.0

ApplicationWindow{
    title: "Parameter Viewer"
    width: 350
    height: 1010
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

        z : 3
        
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
        anchors.bottom: settings_virt_gates.top
        anchors.top: param_viewer.bottom

        Item {
            id: real_gates_tab
            width: parent.width
            height: parent.height

            Rectangle {
                Layout.topMargin : 20
                Layout.leftMargin : 20
                Layout.rightMargin : 20
                Layout.bottomMargin : 20

                width: parent.width
                height: parent.height

                color: "#FFFFFF"

                    
                Component{
                    id : real_voltages_delegate
                    Item{
                        id : var_name_value_item
                        width : parent.width
                        Layout.fillWidth: true
                        height : 45
                        z : 0

                        RowLayout {
                            id: rowLayout5
                            height: 40
                            spacing : 5

                            Rectangle {
                                id: rectangle14
                                height: 40
                                Layout.fillWidth: true
                                Layout.minimumWidth: 100
                                color: "#F5F5F5"
                                Text {
                                    text: gate
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 14
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignRight
                                    anchors.rightMargin: 10
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rectangle14.color= "#E0E0E0"
                                    onExited: rectangle14.color= "#F5F5F5"
                                }


                            }

                            Rectangle{
                                id : real_voltages_deg_rect
                                height : 40
                                Layout.minimumWidth: 100
                                Layout.preferredWidth : 180
                                color : real_voltage_values.focus ? "#8E24AA" : "#E0E0E0" 

                                Rectangle{
                                    anchors.top: parent.top
                                    anchors.left: parent.left
                                    anchors.topMargin: 1
                                    anchors.leftMargin: 1
                                    height : 38
                                    width : real_voltages_deg_rect.width-2
                                    color : "#FFFFFF"
                                    
                                    MouseArea{
                                        height : 38
                                        width : real_voltages_deg_rect.width-2
                                        anchors.fill: parent
                                        propagateComposedEvents: true
                                        hoverEnabled: true

                                        onWheel: {
                                            if (wheel.angleDelta.y < 0 ){
                                                var v = Number.fromLocaleString(Qt.locale(), real_voltage_values.text)
                                                real_voltage_values.text = parseFloat(v-Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            }else{
                                                var v = Number.fromLocaleString(Qt.locale(), real_voltage_values.text)
                                                real_voltage_values.text = parseFloat(v+Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            }
                                            real_gate_model.set_voltage(gate, real_voltage_values.text)
                                        }
                                    }

                                    TextInput {
                                        id: real_voltage_values
                                        text : voltage
                                        width : real_voltages_deg_rect.width-2
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.leftMargin: 5
                                        anchors.topMargin : 10 
                                        font.pointSize: 12

                                        selectByMouse : true
                                        selectedTextColor : '#FFFFFF'
                                        selectionColor : '#EC407A'
                                        onEditingFinished : {
                                                real_gate_model.set_voltage(gate, real_voltage_values.text)
                                                real_voltage_values.text = parseFloat(Number.fromLocaleString(Qt.locale(), real_voltage_values.text)).toFixed(2)

                                                focus = false
                                            }
                                        onActiveFocusChanged: if (activeFocus) {real_voltage_listview.current_item = index}

                                        Keys.onUpPressed: {
                                                var v = Number.fromLocaleString(Qt.locale(), real_voltage_values.text)
                                                real_voltage_values.text = parseFloat(v+Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                                real_gate_model.set_voltage(gate, real_voltage_values.text)
                                            }
                                        Keys.onDownPressed: {
                                                var v = Number.fromLocaleString(Qt.locale(), real_voltage_values.text)
                                                real_voltage_values.text = parseFloat(v-Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                                real_gate_model.set_voltage(gate, real_voltage_values.text)
                                            }
                                    }

                                }
                            }
                            
                            anchors.right: parent.right
                            anchors.rightMargin: 20
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                        }
                    }
                }

                Component{
                    id : real_voltages_delegate_header
                    Item{
                        id : var_name_value_item
                        width : parent.width
                        Layout.fillWidth: true
                        height : 55
                        z: 2

                        RowLayout {
                            id: rowLayout5
                            anchors.right: parent.right
                            anchors.rightMargin: 20
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            anchors.top: parent.top
                            anchors.topMargin: 10
                            height: 40
                            spacing : 5

                            Rectangle {
                                id: rectangle7
                                height: 40
                                color: "#8e24aa"
                                Layout.minimumWidth: 100
                                Layout.fillWidth: true

                                Text {
                                    id: element4
                                    color: "#FFFFFF"
                                    text: qsTr("Gate")
                                    anchors.rightMargin: 10
                                    verticalAlignment: Text.AlignVCenter
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignRight
                                    font.bold: true
                                    font.pixelSize: 18
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rectangle7.color= "#9C27B0"
                                    onExited: rectangle7.color= "#8e24aa"
                                }
                            }

                            Rectangle {
                                id: rectangle15
                                height: 40
                                Layout.minimumWidth: 100
                                Layout.preferredWidth : 180
                                color: "#8e24aa"
                                Text {
                                    id: element7
                                    color: "#FFFFFF"
                                    text: qsTr("Voltage (mV)")
                                    anchors.leftMargin: 10
                                    verticalAlignment: Text.AlignVCenter
                                    font.bold: true
                                    font.pixelSize: 18
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignLeft
                                    anchors.rightMargin: 0
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rectangle15.color= "#9C27B0"
                                    onExited: rectangle15.color= "#8e24aa"
                                }
                            }
                        }
                    }
                }

                ListView {
                    id:real_voltage_listview

                    anchors.fill: parent

                    property int current_item : 0
                    headerPositioning: ListView.OverlayHeader
                    model: real_gate_model
                    delegate: real_voltages_delegate
                    header: real_voltages_delegate_header

                    ScrollBar.vertical: ScrollBar {}
                    
                    Keys.onTabPressed : {
                        current_item ++
                        if (current_item == count){current_item = 0}

                        real_voltage_listview.itemAtIndex(current_item).children[0].children[1].children[0].children[1].focus = true
                        real_voltage_listview.itemAtIndex(current_item).children[0].children[1].children[0].children[1].selectAll()
                    }
                }

            }
        }

        Item {
            id: virtual_gates_tab
            width: parent.width
            height: parent.height

            Rectangle {
                Layout.topMargin : 20
                Layout.leftMargin : 20
                Layout.rightMargin : 20
                Layout.bottomMargin : 20

                width: parent.width
                height: parent.height

                color: "#FFFFFF"

                    
                Component{
                    id : virtual_voltages_delegate
                    Item{
                        width : parent.width
                        Layout.fillWidth: true
                        height : 45

                        RowLayout {
                            height: 40
                            spacing : 5

                            Rectangle {
                                id: rectangle_virt_gates_1
                                height: 40
                                Layout.fillWidth: true
                                Layout.minimumWidth: 100
                                color: "#F5F5F5"
                                Text {
                                    text: gate
                                    verticalAlignment: Text.AlignVCenter
                                    font.pixelSize: 14
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignRight
                                    anchors.rightMargin: 10
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rectangle_virt_gates_1.color= "#EEEEEE"
                                    onExited: rectangle_virt_gates_1.color= "#F5F5F5"
                                }


                            }

                            Rectangle{
                                id : virt_voltages_deg_rect
                                height : 40
                                Layout.minimumWidth: 100
                                Layout.preferredWidth : 180
                                color : virtual_voltage_values.focus ? "#8E24AA" : "#E0E0E0" 

                                Rectangle{
                                    anchors.top: parent.top
                                    anchors.left: parent.left
                                    anchors.topMargin: 1
                                    anchors.leftMargin: 1
                                    height : 38
                                    width : virt_voltages_deg_rect.width-2
                                    color : "#FFFFFF"
                                    
                                    MouseArea{
                                        height : 38
                                        width : virt_voltages_deg_rect.width-2
                                        anchors.fill: parent
                                        propagateComposedEvents: true
                                        hoverEnabled: true

                                        onWheel: {
                                            if (wheel.angleDelta.y < 0 ){
                                                var v = Number.fromLocaleString(Qt.locale(), virtual_voltage_values.text)
                                                virtual_voltage_values.text = parseFloat(v-Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            }else{
                                                var v = Number.fromLocaleString(Qt.locale(), virtual_voltage_values.text)
                                                virtual_voltage_values.text = parseFloat(v+Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            }
                                            virtual_gate_model.set_voltage(gate, virtual_voltage_values.text)
                                        }
                                    }

                                    TextInput {
                                        id: virtual_voltage_values
                                        text : voltage
                                        width : virt_voltages_deg_rect.width-2
                                        anchors.left: parent.left
                                        anchors.top: parent.top
                                        anchors.leftMargin: 5
                                        anchors.topMargin : 10 
                                        font.pointSize: 12

                                        validator : DoubleValidator{bottom :  -1000 ; decimals : 2}
                                        selectByMouse : true
                                        selectedTextColor : '#FFFFFF'
                                        selectionColor : '#EC407A'
                                        onEditingFinished : {
                                                focus = false
                                                virtual_gate_model.set_voltage(gate, virtual_voltage_values.text)
                                                virtual_voltage_values.text = parseFloat(Number.fromLocaleString(Qt.locale(), virtual_voltage_values.text)).toFixed(2)
                                            }
                                        onActiveFocusChanged: if (activeFocus) {virt_voltage_listview.current_item = index}

                                        Keys.onUpPressed:{
                                            var v = Number.fromLocaleString(Qt.locale(), virtual_voltage_values.text)
                                            virtual_voltage_values.text = parseFloat(v+Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            virtual_gate_model.set_voltage(gate, virtual_voltage_values.text)
                                            }
                                        Keys.onDownPressed:{
                                            var v = Number.fromLocaleString(Qt.locale(), virtual_voltage_values.text)
                                            virtual_voltage_values.text = parseFloat(v-Number.fromLocaleString(Qt.locale(), stepsize_step.text)).toFixed(2)
                                            virtual_gate_model.set_voltage(gate, virtual_voltage_values.text)
                                            }
                                    }

                                }
                            }
                            
                            anchors.right: parent.right
                            anchors.rightMargin: 20
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                        }
                    }
                }

                Component{
                    id : virtual_voltages_delegate_header
                    Item{
                        width : parent.width
                        Layout.fillWidth: true
                        height : 55
                        z: 2

                        RowLayout {
                            anchors.right: parent.right
                            anchors.rightMargin: 20
                            anchors.left: parent.left
                            anchors.leftMargin: 10
                            anchors.top: parent.top
                            anchors.topMargin: 10
                            height: 40
                            spacing : 5

                            Rectangle {
                                id: rect_del_header_1
                                height: 40
                                color: "#8e24aa"
                                Layout.minimumWidth: 100
                                Layout.fillWidth: true

                                Text {
                                    id: element4
                                    color: "#FFFFFF"
                                    text: qsTr("Gate")
                                    anchors.rightMargin: 10
                                    verticalAlignment: Text.AlignVCenter
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignRight
                                    font.bold: true
                                    font.pixelSize: 18
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rect_del_header_1.color= "#9C27B0"
                                    onExited: rect_del_header_1.color= "#8e24aa"
                                }
                            }

                            Rectangle {
                                id: rect_del_header_2
                                height: 40
                                Layout.minimumWidth: 100
                                Layout.preferredWidth : 180
                                color: "#8e24aa"
                                Text {
                                    id: element7
                                    color: "#FFFFFF"
                                    text: qsTr("Voltage (mV)")
                                    anchors.leftMargin: 10
                                    verticalAlignment: Text.AlignVCenter
                                    font.bold: true
                                    font.pixelSize: 18
                                    anchors.fill: parent
                                    horizontalAlignment: Text.AlignLeft
                                    anchors.rightMargin: 0
                                }
                                MouseArea {
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    onEntered: rect_del_header_2.color= "#9C27B0"
                                    onExited: rect_del_header_2.color= "#8e24aa"
                                }
                            }
                        }
                    }
                }


                ListView {
                    id:virt_voltage_listview

                    anchors.fill: parent

                    property int current_item : 0

                    headerPositioning: ListView.OverlayHeader
                    model: virtual_gate_model
                    delegate: virtual_voltages_delegate
                    header: virtual_voltages_delegate_header

                    ScrollBar.vertical: ScrollBar {}
                    
                    Keys.onTabPressed : {
                        current_item ++
                        if (current_item == count){current_item = 0}

                        virt_voltage_listview.itemAtIndex(current_item).children[0].children[1].children[0].children[1].focus = true
                        virt_voltage_listview.itemAtIndex(current_item).children[0].children[1].children[0].children[1].selectAll()
                    }
                }

            }
        }
    }

    RowLayout {
        id: settings_virt_gates
        spacing  :0
        height: 50

        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        Rectangle {
            id : step_size_containter
            height: 50
            width : 120
            color : "#F5F5F5"

            Text{
                id : step_size_voltage
                anchors.left: parent.left
                anchors.bottom: parent.bottom
                anchors.leftMargin: 20
                anchors.bottomMargin: 15
                text : 'Stepsize : '
                font.pixelSize: 20
                padding : 0
            }
        }
        Rectangle {
            id : step_size_containter2
            Layout.fillWidth: true
            height: 50
            color : "#F5F5F5"

            Rectangle{
                id : step_size_rect
                height : 40
                width :250
                anchors.top: step_size_containter2.top
                anchors.topMargin: 5
                color : stepsize_step.focus ? "#8E24AA" : "#E0E0E0" 

                Rectangle{
                    anchors.top: parent.top
                    anchors.topMargin: 1
                    anchors.left: parent.left
                    anchors.leftMargin: 1
                    height : 38
                    width : step_size_rect.width-2
                    color : "#FFFFFF"

                    MouseArea{
                        height : 38
                        width : step_size_rect.width-2
                        anchors.fill: parent
                        propagateComposedEvents: true
                        hoverEnabled: true

                        onWheel: {
                            if (wheel.angleDelta.y < 0 ){
                                var v = Number.fromLocaleString(Qt.locale(), stepsize_step.text)
                                stepsize_step.text = parseFloat(Math.round(v/2*10)/10).toFixed(2)
                            }else{
                                var v = Number.fromLocaleString(Qt.locale(), stepsize_step.text)
                                stepsize_step.text = parseFloat(Math.round(v*2*10)/10).toFixed(2)
                            }
                        }
                    }

                    TextInput {
                        id: stepsize_step
                        text : '1.00'
                        width : step_size_rect.width-2
                        anchors.left: parent.left
                        anchors.top: parent.top
                        anchors.leftMargin: 5
                        anchors.topMargin : 10 
                        font.pointSize: 12

                        validator : DoubleValidator{bottom :  0 ; decimals : 2}
                        selectByMouse : true
                        selectedTextColor : '#FFFFFF'
                        selectionColor : '#EC407A'
                        onEditingFinished : {
                                focus = false
                        }
                    }

                }
            }

        }
    }

}