(function () {

"use strict";


const root = document.documentElement;


/* =====================================
   THEME TOGGLE
===================================== */

const themeToggle =
document.getElementById("themeToggle");


function applyTheme(theme){

    root.setAttribute(
        "data-bs-theme",
        theme
    );


    if(themeToggle){

        const icon =
        themeToggle.querySelector("i");


        if(icon){

            icon.className =
            theme === "dark"
            ? "fa-solid fa-sun"
            : "fa-solid fa-moon";

        }

    }

}


let currentTheme="light";

applyTheme(currentTheme);



if(themeToggle){

themeToggle.addEventListener(
"click",
function(){

    currentTheme =
    currentTheme==="light"
    ?"dark"
    :"light";


    applyTheme(currentTheme);

});


}




/* =====================================
   SIDEBAR TOGGLE
===================================== */


const sidebarToggle =
document.getElementById(
"sidebarToggle"
);


const sidebar =
document.getElementById(
"appSidebar"
);



if(sidebarToggle && sidebar){


sidebarToggle.addEventListener(
"click",
function(){


sidebar.classList.toggle(
"show"
);


});


}






/* =====================================
   TOAST SYSTEM
===================================== */


function dismissToast(toast){


if(!toast)
return;


toast.classList.add(
"toast-out"
);



setTimeout(
function(){


if(toast.parentNode){

toast.remove();

}


},
300);


}




document
.querySelectorAll(".app-toast")
.forEach(function(toast){



const close =
toast.querySelector(
".app-toast-close"
);



if(close){


close.addEventListener(
"click",
function(){

dismissToast(toast);

});


}




setTimeout(
function(){

dismissToast(toast);

},
5000);



});








/* =====================================
   CONFIRMATION ALERT
===================================== */


document
.querySelectorAll(
"form[data-confirm]"
)
.forEach(function(form){



form.addEventListener(
"submit",
function(e){


if(form.dataset.confirmed==="true")
return;



e.preventDefault();



const message =
form.dataset.confirm
||
"Are you sure?";




if(window.Swal){


Swal.fire({

title:"Confirm Action",

text:message,

icon:"warning",

showCancelButton:true,


confirmButtonText:
"Yes, Continue",


cancelButtonText:
"Cancel",


confirmButtonColor:
"#4F46E5"



})
.then(function(result){



if(result.isConfirmed){


form.dataset.confirmed="true";

form.submit();


}


});



}

else{


if(confirm(message)){


form.dataset.confirmed="true";

form.submit();


}



}



});


});









/* =====================================
 GLOBAL TOAST FUNCTION
===================================== */


window.showAppToast =
function(message,type="info"){



let stack =
document.getElementById(
"toastStack"
);



if(!stack){


stack=document.createElement(
"div"
);


stack.id="toastStack";


stack.className=
"toast-stack";


document.body.appendChild(
stack
);


}




const icons={

success:
"fa-circle-check",

danger:
"fa-circle-xmark",

warning:
"fa-triangle-exclamation",

info:
"fa-circle-info"

};




const toast =
document.createElement(
"div"
);



toast.className =
"app-toast";



toast.innerHTML=`

<i class="fa-solid ${icons[type] || icons.info}"></i>

<span>
${message}
</span>

<button class="app-toast-close">
×
</button>

`;





toast
.querySelector(
".app-toast-close"
)
.onclick=function(){

dismissToast(toast);

};



stack.appendChild(
toast
);



setTimeout(
function(){

dismissToast(toast);

},
5000);



};



})();
