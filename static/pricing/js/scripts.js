
const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]')
const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl))

const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]')
const popoverList = [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl))

// Get the value of the dir=""
var textDirectionOfTheDom = document.querySelector('html').getAttribute('dir');



/*  
  -------------------------------------------
  -----      JS for loader-wrapper      -----
  -------------------------------------------
*/

window.addEventListener("load", function(event){
    var loaderWrapper = document.querySelector('.loader-wrapper');
    if (loaderWrapper) {
        loaderWrapper.style.display = "none";
    } 

    // initialize the AOS
    if (typeof AOS === 'object') {
        AOS.init({
            offset: 0,
            once: true,
        });
    }
})



/*  
  ---------------------------------------------------------------------
  -----      JS to update all the current year automatically      -----
  ---------------------------------------------------------------------
*/

var currentYear = new Date().getFullYear();
var currentYearTag = document.getElementsByClassName("current-year");

if (currentYearTag.length > 0) {
    for (var i = 0; i < currentYearTag.length; i++) {
        currentYearTag[i].innerHTML = currentYear;
    }
}




/*  
  -----------------------------------------------
  -----      JS for button back to top      -----
  -----------------------------------------------
*/

let btnBackToTop = document.querySelector(".btn-back-to-top");

function backToTop() {
    document.body.scrollTop = 0;
    document.documentElement.scrollTop = 0;
}

// When the user scrolls down 800px from the top of the document, show the button
function scrollbtnBackToTopFun() {
    if ( document.body.scrollTop > 800 || document.documentElement.scrollTop > 800 ) {
        btnBackToTop.style.display = "inline-flex";
    } else {
        btnBackToTop.style.display = "none";
    }
}

window.onscroll = function () {
    if (btnBackToTop) {
        scrollbtnBackToTopFun();
    }
};

// When the user clicks on the button, scroll to the top of the document
if (btnBackToTop) {
    btnBackToTop.addEventListener("click", backToTop);
}



/*  
  -----------------------------------------------------------------  
  -----      JS for changing the price by year and month      -----
  -----------------------------------------------------------------
*/
 
let checkboxPrice = document.querySelector('#checkboxPrice');
if (checkboxPrice) {
    let essential = document.querySelector('.essential');
    let premium = document.querySelector('.premium');
    let advanced = document.querySelector('.advanced');

    let essentialValue = essential.innerText;
    let premiumValue = premium.innerText;
    let advancedValue = advanced.innerText;

    checkboxPrice.addEventListener('click', function (event) {
        if (checkboxPrice.checked == true){
            essential.innerText = essentialValue;
            premium.innerText = premiumValue;
            advanced.innerText = advancedValue;
        } else {
            essential.innerText = Math.floor(essentialValue * (1 + 1/5));
            premium.innerText = Math.floor(premiumValue * (1 + 1/5));
            advanced.innerText = Math.floor(advancedValue * (1 + 1/5));   
        }
    })
}

