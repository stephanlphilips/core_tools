import QtQuick 2.12
import QtQuick.Controls 2.12
import QtQuick.Controls.Material 2.12
import QtQuick.Window 2.2
import QtQuick.Layouts 1.3
import QtQuick.Controls.Styles 1.4


ApplicationWindow{
	width: 1200
    height: 800
    visible: true
    Material.theme: Material.Light

    TabBar {
        id: tabBar
        x: 0
        y: 0
        z: 1
        width: parent.width
        TabButton {
            text: qsTr("User variables")
        }
        TabButton {
            text: qsTr("Autogenerated variables")
        }
    }

    Rectangle {
        id: filler_task_stack
        z : 1
        height: 10
        color: "#FFFFFF"
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.top: tabBar.bottom
    }

    StackLayout {
    	id: stack_layout_var_explorer
        width: parent.width
        anchors.top: filler_task_stack.bottom
        anchors.bottom: parent.bottom
        currentIndex: tabBar.currentIndex

        Layout.fillHeight: true

        Item {
            id: user_varaible_tab
            width: parent.width
            height: parent.height
                
            RowLayout {
                id: user_var_cat_and_content
                spacing: 0
                width: parent.width
                height: parent.height

	            Rectangle {
	                        width: 240
	                        Layout.fillHeight: true
	                        Layout.alignment: Qt.AlignLeft | Qt.AlignTop
	                        color: "#FFFFFF"

	                ColumnLayout {
	                    id: list_view_cat
	                    width : 240
	                    height: parent.height
	                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
	                    spacing: 0
	                    
			            ListModel {
							id : cat_model
						    ListElement {
						        category: "SD voltages"
						    }
						    ListElement {
						        category: "charging energies"
						    }
						    ListElement {
						        category: "tc on/off"
						    }
						    ListElement {
						        category: "Qubit MW properties"
						    }
						}

						Component {
							id : cal_delegate
						    Item {
						        width: parent.width
						        height: 45
						        
						        Rectangle {
					                id: r
					                width: parent.width
						            height: 40
					                color: 'transparent'

					                RowLayout {
					                    id: rowLayout
					                    width: 100
					                    height: 40

					                    Rectangle {
					                    	id : rec_ind
					                        width: 20
					                        height : 40
					                        color: "transparent"
					                        Layout.fillHeight: true
					                    }

					                    Text {
					                        text: category
					                        Layout.alignment: Qt.AlignHLeft | Qt.AlignVCenter
					                        Layout.fillHeight: false
					                        font.pixelSize: 18
					                    }

					                }
					            }

						        Rectangle {
									id: rectangle9
									y : 40
									width: parent.width
									height: 5
									color: "transparent"
								}

						        function hover_in(){
						        	if (list.currentIndex != index){
							        	r.color = "#FAFAFA"
							        	rec_ind.color = "#F8BBD0"
							        	console.log('moved in')
							        }
							    }
						        function hover_out(){
						        	if (list.currentIndex != index){
							        	r.color = "transparent"
							        	rec_ind.color = "transparent"
							        	console.log('moved out')
							        }
						        }

						        function my_click(){
						        	r.color = "transparent"
						        	rec_ind.color = "transparent"
						        	list.currentIndex = index;
						        }
						        MouseArea {
						            anchors.fill: parent
						            hoverEnabled: true
						            onClicked: my_click()
						            onEntered: hover_in()
						            onExited: hover_out()
						        }
						    }
						}

						Component {
						    id: highlightBar

					        Rectangle {
							    width: parent.width
				                height: 0
				                color: "transparent"
				                RowLayout {
				                    height: 40
				                    Rectangle {
				                        width: 20
				                        color: Material.color(Material.Pink)
				                        Layout.fillHeight: true
				                    }
				                    Rectangle {
				                        width: 220
				                        color: "#F5F5F5"
				                        Layout.fillHeight: true
				                    }
				                    spacing : 0
				                }
				            }
						}

						Component{
							id : header_catogories

							Rectangle {
	                        id: header_car
	                        color: "#FFFFFF"
	                        height : 45
	                        width: parent.width

	                        Rectangle {
	                            id: header
	                            width: parent.width
	                            height: 40
	                            color: "#8e24aa"
	                            Layout.preferredHeight: 45
	                            Layout.preferredWidth: parent.width

	                            Text {
	                                id: element5
	                                width: parent.width
	                                height: 40
	                                color : "#FFFFFF"
	                                text: qsTr("Categories")
	                                anchors.leftMargin: 25
	                                anchors.fill: parent
	                                verticalAlignment: Text.AlignVCenter
	                                horizontalAlignment: Text.AlignLeft
	                                font.bold: true
	                                font.pixelSize: 18
	                            }
	                            MouseArea {
						            anchors.fill: parent
						            hoverEnabled: true
						            onEntered: header.color= "#9C27B0"
						            onExited: header.color= "#8e24aa"
						        }
	                        }
	                    }

						}
			            ListView {
							id:list

							width : parent.width
							Layout.fillHeight: true
						    model: cat_model
						    delegate: cal_delegate
						    header:header_catogories
						    highlight: highlightBar
					        focus: true
					        onCurrentItemChanged: console.log(model.get(list.currentIndex).category + ' selected')
						}

					}
				}
				Rectangle {
                    id: rectangle6
                    color: "#ffffff"
                    Layout.preferredWidth: 10
                    Layout.fillHeight: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
                    color: "#FFFFF0"

	                ColumnLayout {
	                    id: lv_cat_cont
	                    width : parent.width
	                    height : parent.height
	                    Layout.alignment: Qt.AlignLeft | Qt.AlignTop
	                    spacing: 0
	                    
	                    ListModel {
							id : variable_name_value_pair_list
						    ListElement {
						        name: "SD_1_on_11"
						        value : "3.2"
						    }
						    ListElement {
						        name: "SD_1_on_10"
						        value : "2.2"
						    }
						    ListElement {
						        name: "SD_1_off"
						        value : "0"
						    }
						    ListElement {
						        name: "SD_2_on"
						        value : "0.5"
						    }
						    ListElement {
						        name: "SD_2_off"
						        value : "0.2"
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
		                                id: textField1

		                                height : 20
		                                width : 250
									    
		                                Layout.minimumWidth: 250
		                                text: value
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
		                                    text: qsTr("Variable Name (unit)")
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
		                                    text: qsTr("Quantity")
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
    }

}
