import QtQuick 2.15
import QtQuick.Controls 2.12
import QtQuick.Layouts 1.3
import QtQuick.Window 2.15
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
                    color: "#FFFFF0"

	                TableView {
	                	id:tableView
				        anchors.fill: parent

				        columnWidthProvider: function (column) { return 100; }
				        rowHeightProvider: function (column) { return 40; }

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
					        		width : 100
					        		height : 40
					                color: "#efefef"
						        	
                                    MouseArea {
                                    	width : 100
                                    	height : 40
							            anchors.fill: parent
							            propagateComposedEvents: true
							            hoverEnabled: true

							            onWheel: {
							            	if (wheel.angleDelta.y < 0 ){
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v += 0.1
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)
								            }else{
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v -= 0.1
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)

								            }
							            }

							            TextInput{
                                            id : text_field_measurment_overview
                                            anchors.right: parent.right
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
					            color: "#222222"
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
					                Rectangle{
					                    width: 100
					                    height: 40
					                    color: '#333333'
						                Text {
						                	anchors.right: parent.right
						                    text: modelData
						                    color : '#FFFFFF'
						                    font.pixelSize: 20
						                    padding: 10
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
					                Label {
					                    width : 50
					                    height : 40
					                    text: modelData
					                    color: '#aaaaaa'
					                    font.pixelSize: 15
					                    padding: 10
					                    verticalAlignment: Text.AlignVCenter

					                    background: Rectangle { color: "#333333" }
					                }
					            }
					        }

					        ScrollIndicator.horizontal: ScrollIndicator { }
					        ScrollIndicator.vertical: ScrollIndicator { }
				    }
	        }}


		}
	}
}



// TableView {
// 			        id: tableView

// 			        columnWidthProvider: function (column) { return 300; }
// 			        rowHeightProvider: function (column) { return 60; }
// 			        anchors.fill: parent
// 			        leftMargin: rowsHeader.implicitWidth
// 			        topMargin: columnsHeader.implicitHeight
// 			        model: TableModel {}
// 			        delegate: Item {
// 			            Text {
// 			                text: display
// 			                anchors.fill: parent
// 			                anchors.margins: 10

// 			                color: '#aaaaaa'
// 			                font.pixelSize: 15
// 			                verticalAlignment: Text.AlignVCenter
// 			            }
// 			        }
// 			        Rectangle { // mask the headers
// 			            z: 3
// 			            color: "#222222"
// 			            y: tableView.contentY
// 			            x: tableView.contentX
// 			            width: tableView.leftMargin
// 			            height: tableView.topMargin
// 			        }

// 			        Row {
// 			            id: columnsHeader
// 			            y: tableView.contentY
// 			            z: 2
// 			            Repeater {
// 			                model: tableView.columns > 0 ? tableView.columns : 1
// 			                Label {
// 			                    width: tableView.columnWidthProvider(modelData)
// 			                    height: 35
// 			                    text: "Column" + modelData
// 			                    color: '#aaaaaa'
// 			                    font.pixelSize: 15
// 			                    padding: 10
// 			                    verticalAlignment: Text.AlignVCenter

// 			                    background: Rectangle { color: "#333333" }
// 			                }
// 			            }
// 			        }
// 			        Column {
// 			            id: rowsHeader
// 			            x: tableView.contentX
// 			            z: 2
// 			            Repeater {
// 			                model: tableView.rows > 0 ? tableView.rows : 1
// 			                Label {
// 			                    width: 180
// 			                    height: tableView.rowHeightProvider(modelData)
// 			                    text: "Row" + modelData
// 			                    color: '#aaaaaa'
// 			                    font.pixelSize: 15
// 			                    padding: 10
// 			                    verticalAlignment: Text.AlignVCenter

// 			                    background: Rectangle { color: "#333333" }
// 			                }
// 			            }
// 			        }

// 			        ScrollIndicator.horizontal: ScrollIndicator { }
// 			        ScrollIndicator.vertical: ScrollIndicator { }
// 			    }