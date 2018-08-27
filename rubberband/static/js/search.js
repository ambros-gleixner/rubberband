
function updateResultsTable() {
    // get formdata by selecting element with id 'form-search'
    form_data = $("#form-search").serializeArray();
    request_data = {};
    $.each( form_data, function( i, field ) {
        request_data[field.name] = field.value;
    });
    exclude = new Array();
    sb = $("#search-base").serializeArray();
    if (sb != "") {
        exclude.push(sb[0].value);
    }
    ec = $(".exclude-compare").serializeArray();
    if (ec != "") {
      for (i = 0; i < ec.length; i++) {
        exclude.push(ec[i].value);
      }
    }
    request_data["exclude_testsets"] = exclude.join(",");
    $.ajax({
        type: "POST",
        url: "search",
        // get request_data from search form
        data: request_data,
        success: function (data){
          fillResultTable(data);
        },
        error:function(){
            alert("Something went wrong.");
        }
    });
}

function fillResultTable(data) {
  // fill resultTable with data,
  // where data should be a htmlstring that just has to be poured into the right container
  //$("#results-table").replaceWith(data);
  $("#results-table").html(data);

  tmp = $("#search-result");
  $.fn.dataTable.moment( 'D. MMM YYYY, HH:mm' );
  if (tmp[0].tagName == "TABLE") {
      tmp.DataTable({
          scrollY: '80vh',
          scrollX: true,
          scroller: true,
          scrollCollapse: true,
          paging: false,
          searching: false,
      });
  }
  // method from static/js/testruns.js
  init_all_stars();
}

$("#search-button").click(function() {
  // on click on search-button, please update the resultstable according to the search fields
  updateResultsTable();
});

$("#reset-search-button").click(function() {
    $("#form-search")[0].reset();
    $("#search-button").click();
});

$(document).ready(function(){
  updateResultsTable();
});
