import QtQuick 2.3
import QtQuick.Window 2.2


Item {
width:Screen.width/2
height:Screen.height/10




Rectangle {
id:rect
color:c
width:Screen.width/2
height:Screen.height/10


Text {
text:name
anchors.centerIn:rect
font.pixelSize:20


}

}

}