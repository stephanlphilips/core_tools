import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Material 2.12

import QtQuick.Layouts 1.3
import QtQuick.Window 2.12


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
                                    spacing : 5
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

                                    Rectangle{
                                    	height : 40
                                        width : 250
	                                    color : ratios_text_field.focus ? "#8E24AA" : "#E0E0E0" 

	                                    Rectangle{
	                                    	anchors.top: parent.top
	                                    	anchors.left: parent.left
	                                        anchors.topMargin: 1
	                                        anchors.leftMargin: 1
	                                    	height : 38
	                                        width : 248
		                                    color : "#FFFFFF"
		                                    
		                                    MouseArea{
	                                    		height : 38
		                                        width : 248
									            anchors.fill: parent
									            propagateComposedEvents: true
									            hoverEnabled: true

									            onWheel: {
									            	if (wheel.angleDelta.y < 0 ){
										            	var v = Number.fromLocaleString(Qt.locale(), ratios_text_field.text)
										            	ratios_text_field.text = parseFloat(v-0.05).toFixed(3)
										            }else{
										            	var v = Number.fromLocaleString(Qt.locale(), ratios_text_field.text)
										            	ratios_text_field.text = parseFloat(v+0.05).toFixed(3)

										            }
									            }
		                                    }

		                                    TextInput {
		                                        id: ratios_text_field
		                                        text : ratios
		                                        width : 248
		                                        anchors.left: parent.left
		                                        anchors.top: parent.top
		                                        anchors.leftMargin: 5
		                                        anchors.topMargin : 10 
		                                        font.pointSize: 12

		                                        validator : DoubleValidator{bottom :  0 ; decimals : 3}
	                                            selectByMouse : true
	                                            selectedTextColor : '#FFFFFF'
	                                            selectionColor : '#EC407A'
	                                            onAccepted : focus = false
		                                    }

	                                    }
                                    }

                                    Rectangle{
                                    	height : 40
                                        width : 250
	                                    color : dbs_text_field.focus ? "#1E88E5" : "#BDBDBD" 

	                                    Rectangle{
	                                    	anchors.top: parent.top
	                                    	anchors.left: parent.left
	                                        anchors.topMargin: 1
	                                        anchors.leftMargin: 1
	                                    	height : 38
	                                        width : 248
		                                    color : "#FFFFFF"
		                                    
		                                    MouseArea{
	                                    		height : 38
		                                        width : 248
									            anchors.fill: parent
									            propagateComposedEvents: true
									            hoverEnabled: true

									            onWheel: {
									            	if (wheel.angleDelta.y < 0 ){
										            	var v = Number.fromLocaleString(Qt.locale(), dbs_text_field.text)
										            	dbs_text_field.text = parseFloat(v-0.5).toFixed(1)
										            }else{
										            	var v = Number.fromLocaleString(Qt.locale(), dbs_text_field.text)
										            	dbs_text_field.text = parseFloat(v+0.5).toFixed(1)

										            }
									            }
		                                    }

		                                    TextInput {
		                                        id: dbs_text_field
		                                        text : db
		                                        width : 248
		                                        anchors.left: parent.left
		                                        anchors.top: parent.top
		                                        anchors.leftMargin: 5
		                                        anchors.topMargin : 10 
		                                        font.pointSize: 12

		                                        validator : DoubleValidator{bottom :  0 ; decimals : 3}
	                                            selectByMouse : true
	                                            selectedTextColor : '#FFFFFF'
	                                            selectionColor : '#EC407A'
	                                            onAccepted : focus = false
		                                    }

	                                    }
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
                                    spacing : 5

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
                                        width : 250
                                        color: "#8e24aa"
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
                                        width : 250
                                        color: "#8e24aa"
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
                // height: parent.height -50
                anchors.bottom : setting_row_virt_mat.top
                anchors.top : parent.top

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

				        columnWidthProvider: function (column) { return 80; }
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
					        		width : 77
					        		height : 40
					                color: "#F5F5F5"

                                    MouseArea {
                                    	width : 77
                                    	height : 40
							            anchors.fill: parent
							            propagateComposedEvents: true
							            hoverEnabled: true

							            onWheel: {
							            	if (wheel.angleDelta.y < 0 ){
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v -= Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)
								            }else{
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v += Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)

								            }
							            }

							            TextInput{
                                            id : text_field_measurment_overview
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.rightMargin: 8
                                            anchors.topMargin: 8
                                            font.pixelSize: 20

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
					                model: ['vP1', 'vP2', 'vP3', 'vP4', 'vP5', 'vP6', 'vB1', 'vB2', 'vB3', 'vB4', 'vB5', 'vB6', 'vvS6', 'vSD1_P', 'vSD2_P']
                                    RowLayout{
                                        spacing : 0
    					                Rectangle{
                                            width : 3
                                            height : 43
                                            color: "#FFFFFF"
                                        }
                                        Rectangle{
    					                    width: 77
    					                    height: 43
    					                    color: '#8E24AA'
    						                Text {
    						                	anchors.right: parent.right
    						                	anchors.top: parent.top
    						                    text: modelData
                                                rightPadding : 8
                                                topPadding : 10
    						                    color : '#FFFFFF'
    						                    font.pixelSize: 18
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
					                model: ['P1', 'P2', 'P3', 'P4', 'P5', 'P6', 'B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'S6', 'SD1_P', 'SD2_P']
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
                                                topPadding : 8 
                                                text: modelData
                                                font.pixelSize : 18
                                                color: "#FFFFFF"
                                            }
                                        }
                                    }
					            }
					        }

					        clip: true
			                ScrollBar.vertical: ScrollBar{
			                	active:  tableVerticalBar.active
			                }
			                ScrollBar.horizontal: ScrollBar{
			                	active:  tableVerticalBar.active
			                }
				    }
	        }}

            RowLayout {
                id: setting_row_virt_mat
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
                    }
                }
            }

		}
	}
}

