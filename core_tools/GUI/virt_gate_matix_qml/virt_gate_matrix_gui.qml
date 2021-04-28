import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.3
import QtQuick.Window 2.12
import QtQuick.Controls.Material 2.12


import Qt.labs.qmlmodels 1.0

ApplicationWindow{
    title: "Data Browser"
    width: 1600
    height: 800
    visible: true
    Material.theme: Material.Light

    TabBar {
        id : virt_matric_gui
        height: 50
        anchors.left: parent.left
        anchors.leftMargin: 0
        anchors.right: parent.right
        anchors.rightMargin: 0
        anchors.top: parent.top
        anchors.topMargin: 0

        TabButton {
            text: qsTr("AWG to dac Ratios")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }

        TabButton {
            text: qsTr("Virtual Gate Matrix")
            anchors.top: parent.top
            anchors.topMargin: 0
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 0
        }
    }

    StackLayout {
        id: stackLayout
        currentIndex: virt_matric_gui.currentIndex
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.top: virt_matric_gui.bottom

        Item {
            id: awg_dac_ratio_tab
            width: parent.width
            height: parent.height

            RowLayout {
                id: user_var_cat_and_content
                spacing: 0
                width: parent.width
                height: parent.height

                Rectangle {
                	Layout.topMargin : 20
                	Layout.leftMargin : 20
                	Layout.rightMargin : 20
                	Layout.bottomMargin : 20
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    color: "#FFFFFF"

                    ColumnLayout {
                        id: lv_cat_cont
                        width : parent.width
                        height : parent.height
                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                        spacing: 0

                        ListModel {
                            id : variable_name_value_pair_list
                            ListElement {
                                name: "P1"
                                ratios : 0.215
                                db : -13.5
                            }
                            ListElement {
                                name: "P2"
                                ratios : 0.215
                                db : -13.5
                            }
                            ListElement {
                                name: "P3"
                                ratios : 0.215
                                db : -13.5
                            }
                            ListElement {
                                name: "P4"
                                ratios : 0.215
                                db : -13.5
                            }
                            ListElement {
                                name: "P5"
                                ratios : 0.215
                                db : -13.5
                            }
                        }

                        Component{
                            id : variable_name_value_pair_delegate
                            Item{
                                id : var_name_value_item
                                width : parent.width
                                Layout.fillWidth: true
                                height : 45

                                RowLayout {
                                    id: rowLayout5
                                    height: 40
                                    anchors.left: parent.left
                                    Rectangle {
                                        id: rectangle14
                                        height: 40
                                        Layout.fillWidth: true
                                        Layout.minimumWidth: 250
                                        color: "#F5F5F5"
                                        Text {
                                            id: element6
                                            text: name
                                            verticalAlignment: Text.AlignVCenter
                                            font.pixelSize: 14
                                            anchors.fill: parent
                                            horizontalAlignment: Text.AlignRight
                                            anchors.rightMargin: 10
                                        }

                                        MouseArea {
                                            anchors.fill: parent
                                            hoverEnabled: true
                                            onEntered: rectangle14.color= "#EEEEEE"
                                            onExited: rectangle14.color= "#F5F5F5"
                                        }


                                    }

                                    TextField {
                                        id: ratios_text_field

                                        height : 20
                                        width : 250

                                        Layout.minimumWidth: 250
                                        text: ratios
                                        Layout.rightMargin: 5
                                        Layout.bottomMargin: -6
                                        Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
                                        font.pointSize: 12
                                    }
                                    TextField {
                                        id: db_ratios_text_field

                                        height : 20
                                        width : 250

                                        Layout.minimumWidth: 250
                                        text: db
                                        Layout.rightMargin: 5
                                        Layout.bottomMargin: -6
                                        Layout.alignment: Qt.AlignLeft | Qt.AlignBottom
                                        font.pointSize: 12
                                    }
                                    anchors.right: parent.right
                                    anchors.rightMargin: 0
                                }
                            }
                        }

                        Component{
                            id : variable_name_value_pair_header
                            Item{
                                id : var_name_value_item
                                width : parent.width
                                Layout.fillWidth: true
                                height : 45

                                RowLayout {
                                    id: rowLayout5
                                    width : parent.width
                                    height: 40

                                    Rectangle {
                                        id: rectangle7
                                        height: 40
                                        color: "#8e24aa"
                                        Layout.minimumWidth: 250
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
                                        color: "#8e24aa"
                                        Layout.rightMargin: 5
                                        Layout.minimumWidth: 250
                                        Text {
                                            id: element7
                                            color: "#FFFFFF"
                                            text: qsTr("Voltage ratio")
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

                                    Rectangle {
                                        id: rectangle156
                                        height: 40
                                        color: "#8e24aa"
                                        Layout.rightMargin: 5
                                        Layout.minimumWidth: 250
                                        Text {
                                            id: element712
                                            color: "#FFFFFF"
                                            text: qsTr("dB")
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
                            id:list_var_name_pair

                            Layout.fillHeight: true
                            Layout.fillWidth: true

                            model: variable_name_value_pair_list
                            delegate: variable_name_value_pair_delegate
                            header: variable_name_value_pair_header
                            focus: true
                            onCurrentItemChanged: console.log(model.get(list_var_name_pair.currentIndex).name + ' selected')
                            ScrollBar.vertical: ScrollBar {}
                        }

                    }
                }

            }

        }

        Item {
            id: virt_gate_matrix_tab
            width: parent.width
            height: parent.height

            RowLayout {
                id: virt_gate_matrix_content
                spacing: 0
                width: parent.width
                height: parent.height

                Rectangle {
                	Layout.topMargin : 20
                	Layout.leftMargin : 20
                	Layout.rightMargin : 20
                	Layout.bottomMargin : 20
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    color: "#FFFFFF"

	                TableView {
	                	id:tableView
				        anchors.fill: parent

				        columnWidthProvider: function (column) { return 100; }
				        rowHeightProvider: function (column) { return 43; }

				        leftMargin: rowsHeader.implicitWidth
				        topMargin: columnsHeader.implicitHeight

				        model: TableModel {
				        	id : model_of_the_table
				            TableModelColumn { display: "checked" }
				            TableModelColumn { display: "amount" }
				            TableModelColumn { display: "fruitType" }
				            TableModelColumn { display: "fruitName" }
				            TableModelColumn { display: "fruitPrice" }

				            // Each row is one type of fruit that can be ordered
				            rows: [
				                {
				                    // Each property is one cell/column.
				                    checked: false,
				                    amount: 1,
				                    fruitType: "Apple",
				                    fruitName: "Granny Smith",
				                    fruitPrice: 1.50
				                },
				                {
				                    checked: true,
				                    amount: 4,
				                    fruitType: "Orange",
				                    fruitName: "Navel",
				                    fruitPrice: 2.50
				                },
				                {
				                    checked: false,
				                    amount: 1,
				                    fruitType: "Banana",
				                    fruitName: "Cavendish",
				                    fruitPrice: 3.50
				                }
				            ]
				        }

				        delegate: 
				        	Item{
				        		Rectangle {
                                    anchors.top: parent.top
                                    anchors.right: parent.right
                                    anchors.topMargin: 3
                                    anchors.leftMargin: 3
					        		width : 97
					        		height : 40
					                color: "#F5F5F5"

                                    MouseArea {
                                    	width : 97
                                    	height : 40
							            anchors.fill: parent
							            propagateComposedEvents: true
							            hoverEnabled: true

							            onWheel: {
							            	if (wheel.angleDelta.y < 0 ){
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v += Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)
								            }else{
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v -= Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)

								            }
							            }

							            TextInput{
                                            id : text_field_measurment_overview
                                            anchors.right: parent.right
                                            anchors.rightMargin: 8
                                            // anchors.rightMargin: 0
                                            font.pixelSize: 28

                                            text : '1'

                                            validator : DoubleValidator{bottom :  0 ; decimals : 3}
                                            selectByMouse : true
                                            selectedTextColor : '#FFFFFF'
                                            selectionColor : '#EC407A'
                                        }
							        }
                                }
						    }

					        Rectangle { // mask the headers
					            z: 3
					            color: "#9C27B0"
					            y: tableView.contentY
					            x: tableView.contentX
					            width: tableView.leftMargin
					            height: tableView.topMargin
					        }

					        Row {
					            id: columnsHeader
					            y: tableView.contentY
					            z: 2
					            Repeater {
					                model: ['P1', 'P2', 'P3', 'P4', 'P5']
                                    RowLayout{
                                        spacing : 0
    					                Rectangle{
                                            width : 3
                                            height : 43
                                            color: "#FFFFFF"
                                        }
                                        Rectangle{
    					                    width: 97
    					                    height: 43
    					                    color: '#8E24AA'
    						                Text {
    						                	anchors.right: parent.right
    						                    text: modelData
                                                rightPadding : 8
    						                    color : '#FFFFFF'
    						                    font.pixelSize: 28
                                                topPadding : 5
    						                }

    					                }
                                    }
					            }
					        }
					        Column {
					            id: rowsHeader
					            x: tableView.contentX
					            z: 2
					            Repeater {
					                model: ['vP1', 'vP2', 'vP3' ]
                                    ColumnLayout{
                                        spacing : 0
                                        Rectangle{
                                            width : 100
                                            height : 3
                                            color : '#FFFFFF'
                                        }
                                        Rectangle{
                                            width : 100
                                            height : 40
                                            color: "#8E24AA"
                                            Text{
                                                anchors.right: parent.right
                                                rightPadding : 8
                                                topPadding : 3 
                                                text: modelData
                                                font.pixelSize : 28
                                                color: "#FFFFFF"
                                            }
                                        }
                                    }
					            }
					        }

					        ScrollIndicator.horizontal: ScrollIndicator { }
					        ScrollIndicator.vertical: ScrollIndicator { }
				    }
	        }}

            RowLayout {
                id: measurement_overview_state_info
                spacing  :0
                height: 50

                anchors.right: parent.right
                anchors.left: parent.left
                anchors.bottom: parent.bottom

                Rectangle {
                    Layout.fillWidth: true
                    height: 50
                    color : "#F5F5F5"

                        Text{
                            id : step_size_descr
                            anchors.left: parent.left
                            anchors.bottom: parent.bottom
                            anchors.leftMargin: 20
                            anchors.bottomMargin: 15
                            text : 'Steptize virtual gate matrix : '
                            font.pixelSize: 20
                            padding : 0
                        }
                        TextField {
                            id : step_size_virt_mat
                            anchors.left: step_size_descr.right
                            anchors.leftMargin: 10
                            text: '0.01'
                            font.pixelSize: 25
                            onAccepted: step_size_virt_mat.focus = false
                        }
                
                }

                // Item {
                // }
                Rectangle {
                    width: 250
                    height: 50
                    color: "#F5F5F5"

                    SwitchDelegate {
                        id: mat_inv
                        height: 50
                        text: qsTr("Inverted Matrix")
                        font.pixelSize: 20
                        Layout.preferredWidth: 250
                        checked: false
                        // onToggled : signal_handler.enable_liveplotting(enable_liveplotting.checked);
                    }
                }
            }

		}
	}
}

