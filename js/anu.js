document.addEventListener ("mouseup",function(event){

    if ((event.button =0)){
        Input.mouse.left =false;

    }
    if ((event.button =1)){
        Input.mouse.middle = false;
    }
    if ((event.button=2)){
        Input.mouse.rigtth=false;
    }
});