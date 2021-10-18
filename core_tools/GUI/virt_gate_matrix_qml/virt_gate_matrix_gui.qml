import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Material 2.12

import QtQuick.Layouts 1.3
import QtQuick.Window 2.12


import Qt.labs.qmlmodels 1.0

ApplicationWindow{
    title: "Virtual gate matrix GUI"
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

        z : 2

        TabButton {
            text: qsTr("AWG to DAC Ratios")
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
                        
                        Component{
                            id : variable_name_value_pair_delegate
                            Item{
                                id : var_name_value_item
                                width : parent.width
                                Layout.fillWidth: true
                                height : 22

                                RowLayout {
                                    id: rowLayout5
                                    height: 20
                                    spacing : 2
                                    anchors.left: parent.left
                                    Rectangle {
                                        id: rectangle14
                                        height: 20
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
                                        height : 20
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
                                                height : 18
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
                                                    ratios_text_field.text = attenuation_model.process_attenuation_update_nrml(index, ratios_text_field.text)
                                                    dbs_text_field.text = parseFloat(Math.log10(Number.fromLocaleString(Qt.locale(), ratios_text_field.text))*20).toFixed(1)

									            }
		                                    }

		                                    TextInput {
		                                        id: ratios_text_field
		                                        text : ratio
		                                        width : 248
		                                        anchors.left: parent.left
		                                        anchors.top: parent.top
		                                        anchors.leftMargin: 5
                                                anchors.topMargin : 0
		                                        font.pointSize: 12

    	                                        validator : DoubleValidator{bottom :  0 ; decimals : 5}
	                                            selectByMouse : true
	                                            selectedTextColor : '#FFFFFF'
	                                            selectionColor : '#EC407A'
	                                            onEditingFinished : {
                                                        text = attenuation_model.process_attenuation_update_nrml(index, text)
                                                        dbs_text_field.text = parseFloat(Math.log10(Number.fromLocaleString(Qt.locale(), text))*20).toFixed(1)
                                                        focus = false
                                                    }
		                                    }

	                                    }
                                    }

                                    Rectangle{
                                        height : 20
                                        width : 250
	                                    color : dbs_text_field.focus ? "#1E88E5" : "#BDBDBD" 

	                                    Rectangle{
	                                    	anchors.top: parent.top
	                                    	anchors.left: parent.left
	                                        anchors.topMargin: 1
	                                        anchors.leftMargin: 1
                                            height : 18
	                                        width : 248
		                                    color : "#FFFFFF"
		                                    
		                                    MouseArea{
                                                height : 18
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
                                                    dbs_text_field.text = attenuation_model.process_attenuation_update_db(index, dbs_text_field.text)
                                                    ratios_text_field.text = parseFloat(10**(Number.fromLocaleString(Qt.locale(), dbs_text_field.text)/20)).toFixed(3)
									            }
		                                    }

		                                    TextInput {
		                                        id: dbs_text_field
		                                        text : db
		                                        width : 248
		                                        anchors.left: parent.left
		                                        anchors.top: parent.top
		                                        anchors.leftMargin: 5
                                                anchors.topMargin : 0
		                                        font.pointSize: 12

		                                        validator : DoubleValidator{bottom :  -60 ; decimals : 3}
	                                            selectByMouse : true
	                                            selectedTextColor : '#FFFFFF'
	                                            selectionColor : '#EC407A'
	                                            onEditingFinished : {
                                                    text = attenuation_model.process_attenuation_update_db(index, text)
                                                    ratios_text_field.text = parseFloat(10**(Number.fromLocaleString(Qt.locale(), text)/20)).toFixed(3)
                                                    focus = false
                                                }
		                                    }

	                                    }
                                    }
                                    
                                    anchors.right: parent.right
                                    anchors.rightMargin: 20
                                }
                            }
                        }

                        Component{
                            id : variable_name_value_pair_header
                            Item{
                                id : var_name_value_item
                                width : parent.width
                                Layout.fillWidth: true
                                height : 22
                                z: 2

                                RowLayout {
                                    id: rowLayout5
                                    anchors.left: parent.left
                                    anchors.right: parent.right
                                    anchors.rightMargin: 20
                                    height: 20
                                    spacing : 2

                                    Rectangle {
                                        id: rectangle7
                                        height: 20
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
                                        height: 20
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
                                        height: 20
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

                            headerPositioning: ListView.OverlayHeader
                            model: attenuation_model
                            delegate: variable_name_value_pair_delegate
                            header: variable_name_value_pair_header
                            focus: true
                            // onCurrentItemChanged: console.log(model.get(list_var_name_pair.currentIndex).name + ' selected')
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
                    Layout.topMargin : 0
                    Layout.leftMargin : 0
                    Layout.rightMargin : 0
                    Layout.bottomMargin : 0
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    color: "#FFFFFF"

	                TableView {
	                	id:tableView
				        anchors.fill: parent

                        columnWidthProvider: function (column) { return 53; }
                        rowHeightProvider: function (column) { return 23; }

				        leftMargin: rowsHeader.implicitWidth
				        topMargin: columnsHeader.implicitHeight

                        property int currentRow : 0
                        property int currentColumn : 0

                        property int active_col : -1
                        property int active_row : -1
				        model: vg_matrix_model

				        delegate: 
				        	Item{
				        		Rectangle {
                                    anchors.top: parent.top
                                    anchors.right: parent.right
                                    anchors.topMargin: 3
                                    anchors.leftMargin: 3
                                    width : 50
                                    height : 20
                                    color:{
                                        if ((tableView.active_col === column && tableView.active_row === row) && !(text_field_measurment_overview.text > 0.001 || text_field_measurment_overview.text < -0.001)){'#E0E0E0'}
                                        else if ((tableView.active_col === column && tableView.active_row === row) && (text_field_measurment_overview.text > 0.001 || text_field_measurment_overview.text < -0.001)){'#FA0000'}
                                        else if ((tableView.active_col === column || tableView.active_row === row) && !(text_field_measurment_overview.text > 0.001 || text_field_measurment_overview.text < -0.001)){'#EEEEEE'}
                                        else if ((tableView.active_col === column || tableView.active_row === row) && (text_field_measurment_overview.text > 0.001 || text_field_measurment_overview.text < -0.001)){'#FF5555'}
                                        else if (text_field_measurment_overview.text > 0.001 || text_field_measurment_overview.text < -0.001 ){'#FFAAAA'}
                                        else {'#F5F5F5'}
                                    }

                                    MouseArea {
                                        width : 50
                                        height : 20
							            anchors.fill: parent
							            propagateComposedEvents: true
							            hoverEnabled: true

							            onWheel: {
							            	if (wheel.angleDelta.y < 0 ){
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v -= Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)
                                                vg_matrix_model.update_vg_matrix(row, column, text_field_measurment_overview.text)
								            }else{
								            	var v = Number.fromLocaleString(Qt.locale(), text_field_measurment_overview.text)
								            	v += Number.fromLocaleString(Qt.locale(), step_size_virt_mat.text)
								            	text_field_measurment_overview.text = parseFloat(v).toFixed(3)
                                                vg_matrix_model.update_vg_matrix(row, column, text_field_measurment_overview.text)
								            }
							            }

                                        onClicked: {
                                            text_field_measurment_overview.focus = true
                                        }

                                        onEntered: {
                                            columnsHeader_repeater.itemAt(column).children[1].color =  '#EC407A'
                                            rowHeader_repeater.itemAt(row).children[1].color =  '#EC407A'

                                            tableView.active_col = column
                                            tableView.active_row = row

                                        }
                                        onExited : {
                                            columnsHeader_repeater.itemAt(column).children[1].color =  '#8E24AA'
                                            rowHeader_repeater.itemAt(row).children[1].color =  '#8E24AA'

                                            tableView.active_col = -1
                                            tableView.active_row = -1                                      
                                        }
							            TextInput{
                                            id : text_field_measurment_overview
                                            anchors.right: parent.right
                                            anchors.top: parent.top
                                            anchors.rightMargin: 4
                                            anchors.topMargin: 0
                                            font.pixelSize: 15

                                            text : vg_matrix_data

                                            validator : DoubleValidator{bottom :  -100 ; decimals : 3}
                                            selectByMouse : true
                                            selectedTextColor : '#FFFFFF'
                                            selectionColor : '#EC407A'
                                            onEditingFinished : {
                                                vg_matrix_model.update_vg_matrix(row, column, text_field_measurment_overview.text)
                                                focus = false
                                            }
                                            onActiveFocusChanged: if (activeFocus) {tableView.currentColumn = column;tableView.currentRow = row }
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
                                id : columnsHeader_repeater
				                model: column_header_model
                                
                                delegate : 
                                    RowLayout{
                                        spacing : 0
    					                Rectangle{
                                            width : 3
                                            height : 23
                                            color: "#FFFFFF"
                                        }
                                        Rectangle{
                                            width: 50
                                            height: 23
    					                    color: '#8E24AA'
    						                Text {
    						                	anchors.right: parent.right
    						                	anchors.top: parent.top
    						                    text: HeaderName
                                                rightPadding : 4
                                                topPadding : 0
    						                    color : '#FFFFFF'
                                                font.pixelSize: 15
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
				                model: row_header_model
                                id : rowHeader_repeater
                                ColumnLayout{
                                    spacing : 0
                                    Rectangle{
                                        width : 70
                                        height : 3
                                        color : '#FFFFFF'
                                    }
                                    Rectangle{
                                        width : 70
                                        height : 20
                                        color: "#8E24AA"
                                        Text{
                                            anchors.right: parent.right
                                            rightPadding : 4
                                            topPadding : 0
                                            text: HeaderName
                                            font.pixelSize : 15
                                            color: "#FFFFFF"
                                        }
                                    }
                                }
				            }
				        }

				        clip: true
		                ScrollBar.vertical: ScrollBar{
		                }
		                ScrollBar.horizontal: ScrollBar{
		                }

                        Keys.onTabPressed : {
                            console.log(currentRow, currentColumn)
                            currentColumn ++
                            var current_cell_number  = 3+currentRow*tableView.rows + currentColumn

                            if (currentRow+1 == tableView.rows && currentColumn == tableView.columns){
                                current_cell_number = 3
                            }
                            // More generic way neeeded to access, this messes up on resize
                            tableView.children[0].children[current_cell_number].children[0].children[0].children[0].focus = true
                            tableView.children[0].children[current_cell_number].children[0].children[0].children[0].selectAll()
                        }
				    }
    	        }
            }

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
                            text : 'Stepsize virtual gate matrix : '
                            font.pixelSize: 20
                            padding : 0
                        }
                        TextField {
                            id : step_size_virt_mat
                            anchors.left: step_size_descr.right
                            anchors.leftMargin: 10
                            text: '0.01'
                            font.pixelSize: 25
                            onEditingFinished: {
                                step_size_virt_mat.focus = false}
                        }
                
                }

                // Rectangle {
                //     width: 250
                //     height: 50
                //     color: "#F5F5F5"

                //     SwitchDelegate {
                //         id: mat_norm
                //         height: 50
                //         text: qsTr("Normalize Matrix")
                //         font.pixelSize: 20
                //         Layout.preferredWidth: 250
                //         checked: false
                //         onToggled: vg_matrix_model.manipulate_matrix(mat_inv.checked, mat_norm.checked)

                //     }
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
                        onToggled: vg_matrix_model.manipulate_matrix(mat_inv.checked, false)
                        objectName: "mat_inv_switch"
                    }
                }
            }

		}
	}
}

