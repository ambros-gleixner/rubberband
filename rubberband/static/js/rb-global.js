/* ############### global vars ############### */
var path = window.location.pathname;
var end = path.split("/");
var debug = "";

/* ############### functions ############### */

function set_active_tab(route) {
  /* highlight the current page in the navbar */
  $(".rb-navbar li").removeClass("active");
  $(`.rb-navbar li a[href="/${route}"]`).parent("li").addClass("active");
}

function goBack() {
  /* go back in history */
  window.history.back();
}

function init_datetimepicker(id) {
  $('#'+id).datetimepicker({ format: 'YYYY-MM-DD' });
}

function get_query_params(query_string) {
  /* utility method that parses a query string */
  var match,
    pl     = /\+/g,  // Regex for replacing addition symbol with a space
    search = /([^&=]+)=?([^&]*)/g,
    decode = function (s) { return decodeURIComponent(s.replace(pl, " ")); },
    query  = query_string.substring(1);

  params = {};
  while (match = search.exec(query))
    params[decode(match[1])] = decode(match[2]);

  return params;
}

function jsonlog(val) {
  console.log(JSON.stringify(val));
}

function rb_error(){
  alert("Rubberband got tangled up, it looks like something went wrong.");
}

function getCookie(name) {
  var r = document.cookie.match("\\b" + name + "=([^;]*)\\b");
  return r ? r[1] : undefined;
}

// add listener to file selectors
$(document).ready(function(){
  $('input[type="file"]').change(function(e){
    let files = e.target.files;
    let content = "Choose file ..."
    if (files.length == 1) {
      content = files[0].name;
    } else if (files.length > 1) {
      content = files.length + " files selected";
    }
    $('label.custom-file-label[for='+this.id+']').html(content);
  });
});


/* ############### exeuction ############### */

set_active_tab(end[1]);

