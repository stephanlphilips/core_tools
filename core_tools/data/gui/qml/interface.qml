import QtQuick 2.10
import QtQuick.Window 2.10
import QtQuick.Controls 1.4
import QtQuick.Controls.Styles 1.4
import QtQuick.Layouts 1.3

import QtQuick.Controls.Material 2.12



Window {
    visible: true
    width: 640
    height: 480
    title: qsTr("Hello World")

    Material.theme: Material.Dark
    Material.accent: Material.Purple

    Component { // 'real'  delegate
            id: highlightBar
            Rectangle {
                width: listView.currentItem.width/10;
                height: listView.currentItem.height
                color: "#FFFF88"
                y: listView.currentItem.y
                z:2
                anchors.right:parent.right
                Behavior on y { SpringAnimation { spring: 4; damping: 0.5 } }
            }
        }
        
    Rectangle {
        id:background
        width: 200; height: parent.height
        ListModel {
            id: myModel
            ListElement {
                textButtonR: "Open"
                textButtonL: "Close"
                imageSource: "spin.png"
            }
            ListElement {
                textButtonR: "Open"
                textButtonL: "Close"
                imageSource: "spin.png"
            }
            ListElement {
                textButtonR: "Open"
                textButtonL: "Close"
                imageSource: "spin.png"
            }

        }


        //Delegate
        Component {
            id: del
            Rectangle{
                id: r
                height: 90
                width: 200
                color:'indigo'
                border.width:ListView.isCurrentItem ? 2 : 0 // you can have a 'real delegate' like  highlightBar  OR simply change the delegate when item is currentItem
                property string _textButtonR: textButtonR
                property string _imageSource: imageSource

                Column{
                    anchors.fill: parent
                    Image{
                        source:_imageSource
                        height: 20
                        width: 20

                    }
                    Text{
                        text:_textButtonR
                        color : 'white'
                    }
                    Button{
                        id:_btn
                        text: "btn :" + index

                    }

                }

                function btnClick(_ind){
                   console.log("btn" +_ind + "click")
                }
                function delegateClick(_ind){
                    console.log("delegate click; index " +  _ind)
                    listView.currentIndex=_ind

                }

                MouseArea{
                    anchors.fill: parent
                    propagateComposedEvents: true
                    onClicked: _btn.hovered ? r.btnClick(index) : r.delegateClick(index)  // the test
                }
            }

        }

        //highlight
        

        ListView {
            id: listView
            width: 200;
            height: parent.height
            model: myModel
            delegate: del
            clip: true
            focus:true
            highlight: highlightBar
            highlightFollowsCurrentItem: false

        }
    }
}