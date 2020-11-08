import QtQuick 2.4

import QtQuick.Controls 2.3

Item {
    property int decimals: 2
    property real realValue: 0.0
    property real realFrom: -Infinity
    property real realTo: 100.0
    property real realStepSize: 0.1
    property real factor: Math.pow(10, decimals)
    property real stepSize: realStepSize*factor
    property real value: realValue*factor

    TextField{
        id: spinbox
        // to : realTo*factor
        // from : realFrom*factor
        // validator: DoubleValidator {
        //     bottom: Math.min(spinbox.from, spinbox.to)*spinbox.factor
        //     top:  Math.max(spinbox.from, spinbox.to)*spinbox.factor
        // }

        placeholderText: function(value, locale) {
            return parseFloat(value*1.0/factor).toFixed(decimals);
        }

        // MouseArea {
        //     anchors.fill: spinbox

        //     function scoll_event(angle){
        //         if (angle < 0)
        //             spinbox.value += spinbox.stepSize
        //         else
        //             spinbox.value -= spinbox.stepSize
                
        //     }

        //     onWheel: scoll_event(wheel.angleDelta.y)
        //     // onEntered: console.log('hover detedted in')
        //     // onExited: console.log('hover detedted')

        // }
    }

}

// onWheel: {
//                 if (wheel.angleDelta.y > 0){
//                                         value += stepSize;
//                                         console.log('scoll detedted in')}
//                 else
//                     value -= stepSize;
//                 }
//             }