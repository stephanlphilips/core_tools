import QtQuick.Window 2.2
import QtQuick 2.3




Window {
visible:true
width:Screen.width/2
height:Screen.height/2


ListView {
width:Screen.width/2
height:Screen.height/2


// Point to the model


model:mod


delegate:MyDel{}

}


MyModel{id:mod}


}