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

    StackLayout {
        id: stackLayout
        currentIndex: 0
        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: measurement_overview_state_info.top
        anchors.top: parent.top

        Item{
        	ColumnLayout{
                id: overview_tab_col_layout
                anchors.fill: parent
                transformOrigin: Item.TopLeft

                RowLayout {
                    id: overview_select_sample
                    Layout.leftMargin: 20
                    Layout.rightMargin: 30
                    transformOrigin: Item.TopLeft
                    Layout.fillHeight: false
                    Layout.fillWidth: true

                    RowLayout {
                        Text {
                            Layout.preferredWidth: 60
                            height: 30
                            text: 'Project'
                            font.pixelSize: 16
                        }

                        ComboBox {
                            objectName : 'combobox_project'
                            id: combobox_project
                            model : combobox_project_model
                            Layout.preferredWidth: 200
                            Layout.margins: 2
                            onActivated : signal_handler.pro_set_sample_info_state_change(combobox_project.currentIndex, combobox_set_up.currentIndex, combobox_sample.currentIndex);

                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Text {
                            Layout.preferredWidth: 50
                            height: 30
                            text: 'Setup'
                            font.pixelSize: 16
                        }

                        ComboBox {
                            objectName : 'combobox_set_up'
                            id: combobox_set_up
                            model : combobox_set_up_model
                            Layout.preferredWidth: 150
                            Layout.margins: 2
                            onActivated : signal_handler.pro_set_sample_info_state_change(combobox_project.currentIndex, combobox_set_up.currentIndex, combobox_sample.currentIndex);
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Text {
                            Layout.preferredWidth: 60
                            height: 30
                            text: 'Sample'
                            font.pixelSize: 16
                        }

                        ComboBox {
                            objectName : 'combobox_sample'
                            id: combobox_sample
                            model : combobox_sample_model
                            Layout.preferredWidth: 250
                            Layout.margins: 2
                            onActivated : signal_handler.pro_set_sample_info_state_change(combobox_project.currentIndex, combobox_set_up.currentIndex, combobox_sample.currentIndex);

                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    Rectangle{
                        width : 20
                        height : 20
                        Layout.leftMargin : 15
                        Layout.topMargin : 4
                        color : 'transparent'
                        Star_shape{
                            anchors.fill: parent
                            size : 20
                            uuid_ : 'filter'
                            selected : false
                        }
                    }
                    Item {
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Rectangle {
                            Layout.preferredWidth: 50
                            height: 30
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 5
                                anchors.topMargin : 5
                                text: 'Name'
                                font.pixelSize: 16
                            }
                        }
                        Rectangle {
                            color : '#FFFFFF'
                            Layout.preferredWidth: 150
                            height: 30
                            border.color: '#C0C0C0'
                            border.width: 1
                            TextInput{
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 5
                                anchors.topMargin : 5
                                width : parent.width-2
                                property string filter_name
                                objectName : 'input_name'
                                id : input_name
                                font.pixelSize: 16
                                text : filter_name
                                selectByMouse : true
                                selectedTextColor : '#FFFFFF'
                                selectionColor : '#EC407A'
                                onEditingFinished : {
                                    if (filter_name != input_name.text){
                                        signal_handler.update_name_filter(input_name.text);
                                        filter_name = input_name.text
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        Layout.fillWidth: true
                    }

                    RowLayout {
                        Rectangle {
                            Layout.preferredWidth: 80
                            height: 30
                            Text {
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 5
                                anchors.topMargin : 5
                                text: 'Keywords'
                                font.pixelSize: 16
                            }
                        }
                        Rectangle {
                            color : '#FFFFFF'
                            Layout.preferredWidth: 280
                            height: 30
                            border.color: '#C0C0C0'
                            border.width: 1
                            TextInput{
                                anchors.left: parent.left
                                anchors.top: parent.top
                                anchors.leftMargin: 5
                                anchors.topMargin : 5
                                width : parent.width-2
                                property string filter_keywords
                                objectName : 'input_keywords'
                                id : input_keywords
                                font.pixelSize: 16
                                text : filter_keywords
                                selectByMouse : true
                                selectedTextColor : '#FFFFFF'
                                selectionColor : '#EC407A'
                                onEditingFinished : {
                                    if (filter_keywords != input_keywords.text){
                                        signal_handler.update_keywords_filter(input_keywords.text);
                                        filter_keywords = input_keywords.text
                                    }
                                }
                            }
                        }
                    }
                }

                RowLayout {
                    id: measurement_overview_layout
                    Rectangle{
                    	color: "#FFFFFFFF"
                        Layout.fillHeight: true
                        Layout.leftMargin: 10
                        Layout.rightMargin: 10
                        width : 180
                        radius : 5

                        ListView {
                        	Component {
	                            id : date_list_delegate
	                            Item {
	                                width: parent.width
	                                height: 36

	                                Rectangle {
	                                    id: r
	                                    width: parent.width-20
	                                    x: 10
	                                    height: 36
	                                    radius : 5
	                                    color: 'transparent'

	                                    RowLayout {
	                                        width: 100
	                                        height: 34
	                                        spacing : 10
	                                        Rectangle {
	                                            id : rec_ind
	                                            width: 12
	                                            radius : 5
	                                            height : 34
	                                            color: "transparent"
	                                            Layout.fillHeight: true
	                                        }

	                                        Text {
	                                            text: date
	                                            Layout.alignment: Qt.AlignHLeft | Qt.AlignVCenter
	                                            Layout.fillHeight: false
	                                            font.pixelSize: 16
	                                        }

	                                    }
	                                }

	                                Rectangle {
	                                    y : 36
	                                    width: parent.width
	                                    height: 5
	                                    color: "transparent"
	                                }

	                                function hover_in(){
	                                    if (date_list_view.currentIndex != index){
	                                        r.color = "#FAFAFA"
	                                        rec_ind.color = "#F8BBD0"
	                                    }
	                                }
	                                function hover_out(){
	                                    if (date_list_view.currentIndex != index){
	                                        r.color = "transparent"
	                                        rec_ind.color = "transparent"
	                                    }
	                                }

	                                function my_click(){
	                                    r.color = "transparent"
	                                    rec_ind.color = "transparent"
	                                    date_list_view.currentIndex = index;
	                                }
	                                MouseArea {
	                                    anchors.fill: parent
	                                    hoverEnabled: true
	                                    onClicked: {my_click(); focus=true}
	                                    onEntered: hover_in()
	                                    onExited: hover_out()
	                                }
	                            }
	                        }

	                        Component {
	                            id: date_list_highlight

	                            Rectangle {
	                            	id : date_list_highlight_box
	                                height: 0
	                                color: "transparent"
	                                width: measurement_overview_layout.width
                                    x: 10

	                                RowLayout {
	                                    height: 36
	                                    Rectangle {
	                                    	x : 10
	                                        width: 12
	                                        radius : 5
	                                        color: Material.color(Material.Pink)
	                                        Layout.fillHeight: true
	                                    }
	                                    Rectangle {
	                                        width: 210
	                                        radius : 5
	                                        color: "#F5F5F5"
	                                        Layout.fillHeight: true
	                                    }
	                                    spacing : 0
	                                }
	                            }
	                        }

	                        Component{
	                            id : date_list_header

	                            Rectangle {
	                                id: header_car
	                                color: "#FFFFFF"

	                                width: parent.width
	                                height : 40 + 20
	                                radius : 5

	                                Rectangle {
	                                    id: header
	                                    width: parent.width-10
	                                    height: 40
	                                    x : 10
	                                    y : 10

	                                    radius : 5
	                                    color: "#8e24aa"

	                                    Text {
	                                        width: parent.width
	                                        height: 30
	                                        color : "#FFFFFF"
	                                        text: qsTr("Date")
	                                        anchors.leftMargin: 25
	                                        anchors.fill: parent
	                                        verticalAlignment: Text.AlignVCenter
	                                        horizontalAlignment: Text.AlignLeft
	                                        font.bold: true
	                                        font.pixelSize: 16
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
                            objectName : 'date_list_view'
                            id: date_list_view
                            width: parent.width
                            height : parent.height
                            delegate: date_list_delegate
                            highlight: date_list_highlight
                            header : date_list_header
                            spacing : 10
                            clip : true
                            model: date_list_model
                            onCurrentItemChanged: signal_handler.update_date_selection(date_list_view.currentIndex)
                        }
                    }

                    Rectangle {
                        color: "#FFFFFFFF"

                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.rightMargin: 10
                        radius : 5

                        ListView {
                            id: data_content_view
                            height : parent.height
                            width : parent.width
                            spacing: 10
                            clip : true

                        	Component {
                                id : data_content_view_delegate

                                Rectangle {
                                    id: row_overview
                                    height: 36
                                    width: data_content_view.width

                                    color: "#F5F5F5"
                                    radius : 5
                                    RowLayout {
                                        id: rowLayout115
                                        width: row_overview.width
                                        height: row_overview.height

                                        Rectangle{
                                            width : 20
                                            height : 20
                                            Layout.leftMargin : 15
                                            Layout.topMargin : 4
                                            color : 'transparent'
                                            Star_shape{
                                                anchors.fill: parent
                                                size : 20
                                                uuid_ : uuid
                                                selected : starred
                                            }
                                        }

                                        TextEdit {
                                            height: 36
                                            text: id_
                                            focus : true
                                            readOnly : true
                                            selectByMouse : true
                                            font.pixelSize: 15
                                            Layout.preferredWidth: 80
                                            Layout.leftMargin: 20
                                        }

                                        TextEdit {
                                            text: uuid
                                            focus : true
                                            readOnly : true
                                            selectByMouse : true
                                            font.pixelSize: 15
                                            Layout.preferredWidth: 200
                                        }

                                        Text {
                                            text: date
                                            font.pixelSize: 15
                                            Layout.preferredWidth: 100
                                        }

                                        Item{
                                            height: 36
                                            TextInput{
                                                id : text_field_measurment_overview
                                                z : 1
                                                y : (36-18)/2
                                                height: 40
                                                Layout.preferredWidth: text_field_measurment_overview.contentWidth
                                                font.pixelSize: 15
                                                text : name
                                                selectByMouse : true
                                                selectedTextColor : '#FFFFFF'
                                                selectionColor : '#EC407A'
                                                onEditingFinished : {
                                                    if (name != text_field_measurment_overview.text){
                                                        signal_handler.update_name_meaurement(uuid,text_field_measurment_overview.text);
                                                    }
                                                }
                                            }
                                        }

                                        Item {
                                            id: element31
                                            width: 200
                                            height: 36
                                            Layout.fillWidth: true
                                        }

                                        Text {
                                            id: element32
                                            text: keywords
                                            Layout.rightMargin: 20
                                            font.pixelSize: 15
                                        }
                                    }

                                    MouseArea {
                                        anchors.fill: parent
                                        hoverEnabled: true
                                        onEntered: row_overview.color= "#EEEEEE"
                                        onExited: row_overview.color= "#F5F5F5"
                                        onDoubleClicked : signal_handler.plot_ds_qml(uuid);
                                        onClicked : focus = true;
                                        z : -1
                                    }
                                }

                            }

                            Component{
                                id : data_content_view_header
                                Rectangle{
                                    anchors.right: parent.right
                                    anchors.left: parent.left

                                    height : 40+20

	                                Rectangle {
	                                    id: data_content_view_header_box
	                                    height: 40

	                                    color: "#8E24AA"
	                                    anchors.left: parent.left
	                                    anchors.right: parent.right
	                                    anchors.top: parent.top
	                                    anchors.topMargin: 10
	                                    radius : 5
	                                    RowLayout {
	                                        id: rowLayout
	                                        width: data_content_view_header_box.width
	                                        height: data_content_view_header_box.height

	                                        Rectangle{
	                                            width : 20
	                                            height : 20
	                                            Layout.leftMargin : 15
	                                            Layout.topMargin : 4
	                                            color : 'transparent'
	                                            Star_shape{
	                                                anchors.fill: parent
	                                                size : 20
	                                            }
	                                        }

	                                        Text {
	                                            text: qsTr("ID")
	                                            color : 'white'
	                                            Layout.leftMargin: 20
	                                            Layout.preferredWidth: 80
	                                            font.bold: true
	                                            font.pixelSize: 16
	                                        }

	                                        Text {
	                                            text: qsTr("UUID")
	                                            color : 'white'
	                                            Layout.preferredWidth: 200
	                                            font.bold: true
	                                            font.pixelSize: 16
	                                        }


	                                        Text {
	                                            text: qsTr("Time")
	                                            color : 'white'
	                                            Layout.preferredWidth: 100
	                                            Layout.fillWidth: false
	                                            font.bold: true
	                                            font.pixelSize: 16
	                                        }

	                                        Text {
	                                            text: qsTr("Name")
	                                            color : 'white'
	                                            font.bold: true
	                                            font.pixelSize: 16
	                                        }


	                                        Item {
	                                            width: 200
	                                            height: data_content_view_header_box.height
	                                            Layout.fillWidth: true
	                                        }

	                                        Text {
	                                            text: qsTr("Keywords")
	                                            color : 'white'
	                                            Layout.rightMargin: 20
	                                            font.bold: true
	                                            font.pixelSize: 16
	                                        }

	                                    }

	                                    MouseArea {
	                                        anchors.fill: parent
	                                        hoverEnabled: true
	                                        onEntered: data_content_view_header_box.color= "#9C27B0"
	                                        onExited: data_content_view_header_box.color= "#8e24aa"
	                                    }
	                                }
                                }
                            }

                            delegate: data_content_view_delegate
                            header : data_content_view_header
                            model:data_content_view_model

                            flickableDirection: Flickable.VerticalFlick
                            boundsBehavior: Flickable.StopAtBounds

                            ScrollBar.vertical: ScrollBar {}
                        }
                    }
                }
			}
        }
    }

    RowLayout {
    	id: measurement_overview_state_info
        height: 50

        anchors.right: parent.right
        anchors.left: parent.left
        anchors.bottom: parent.bottom

        Rectangle {
            width: 250
            height: 50
            color : "transparent"
            Layout.preferredWidth: 250

            RadioButton {
                objectName : 'local_conn'
                id : local_conn
                property var local_conn_status
                Material.accent: (local_conn.local_conn_status == true) ? Material.Teal : Material.Red
                width: 250
                height: 50
                text: " Local Connection"
                leftPadding: 15
                checkable: false
                display: AbstractButton.TextBesideIcon
                checked: true
            }
        }

        Rectangle {
            width: 250
            height: 50
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.preferredWidth: 250
            color : "transparent"

            RadioButton {
                objectName : 'remote_conn'
                id : remote_conn
                property var remote_conn_status
                Material.accent: (remote_conn.remote_conn_status == true) ? Material.Teal : Material.Red
                width: 250
                height: 50
                text: 'Remote Connection'
                leftPadding: 15
                checkable: false
                checked: true
            }
        }

        Item {
            Layout.fillWidth: true
        }

        Rectangle {
            width: 120
            height: 50
            Layout.alignment: Qt.AlignLeft | Qt.AlignTop
            Layout.preferredWidth: 120
            color : "transparent"

            Button {
                objectName : 'close_plots'
                id : close_plots
                width: 120
                height: 50
                text: 'Close all plots'
                font.capitalization: Font.MixedCase
                leftPadding: 15
                onClicked: signal_handler.close_all_plots()
            }
        }

        SwitchDelegate {
            objectName : 'enable_liveplotting'
            id: enable_liveplotting
            height: 50
            text: qsTr("Enable liveplotting")
            Layout.preferredWidth: 250
            checked: true
            onToggled : signal_handler.enable_liveplotting(enable_liveplotting.checked);
        }
    }
    // move focus out of text input when clicking somewhere
    MouseArea {
        anchors.fill: parent
        onPressed: (mouse) => {
            mouse.accepted = false
            focus = true
            }
    }
}