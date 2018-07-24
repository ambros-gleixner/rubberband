Array.prototype.allValuesSame = function() {

    for(var i = 1; i < this.length; i++)
    {
        if(this[i] !== this[0])
            return false;
    }

    return true;
}
var table;
var meta_table;
var settings_table;
formatResultTables();
formatMetaTable();
formatSettingsTable();
$(".bs-tooltip").tooltip();
$("a.bs-popover").popover();
$("#toggle-settings").bootstrapToggle()
$(function() {
    $("#toggle-settings").change(function() {
        var elements = $(".toggle_settings_hide");
        var displaystyle = "";
        if ($(this).prop('checked')) {
            displaystyle = "none";
        }
        for(var i=0; i<elements.length; i++){
            elements[i].style.display = displaystyle;
        }
    })
})
$("#toggle-meta").bootstrapToggle()
$(function() {
    $("#toggle-meta").change(function() {
        var elements = $(".toggle_meta_hide");
        var displaystyle = "";
        if ($(this).prop('checked')) {
            displaystyle = "none";
        }
        for(var i=0; i<elements.length; i++){
            elements[i].style.display = displaystyle;
        }
    })
})
/* adjust tables */
$('a[data-toggle="tab"]').on('shown.bs.tab', function(e) {
    $($.fn.dataTable.tables(true)).DataTable().columns.adjust();
});
// if compare is in query string, then we are in the compare view but only in a comparison to exactly one
//if ((window.location.search.indexOf("compare") >= 0) && !(window.location.valueOf("compare").toString().includes(","))) {

// if compare is in query string, then we are in the compare view
if (window.location.search.indexOf("compare") >= 0) {
  /* red = new Color(245, 50, 50);
  green = new Color(50, 245, 50); */
  dark_gray = new Color(160, 160, 160);
  gray = new Color(200, 200, 200);
  white = new Color(255, 255, 255);
  red = new Color(240, 40, 150);
  green = new Color(130, 200, 30);
  colorateCells();
}

function formatMetaTable() {
    meta_table = $('.meta-table').DataTable({
        scrollY: '80vh',
        scrollX: true,
        scroller: true,
        scrollCollapse: true,
        paging: false,
    });
}

function formatSettingsTable() {
    settings_table = $('.settings-table').DataTable({
        scrollY: '80vh',
        scrollX: true,
        scroller: true,
        scrollCollapse: true,
        paging: false,
    });
}

function formatResultTables() {
    table = $('.results-table').DataTable({
        scrollY: '80vh',
        scrollX: true,
        scroller: true,
        scrollCollapse: true,
        paging: false,
        columnDefs: [
            { type: 'any-number', targets: 'number' },
        ]
    });

    $('.nav-tabs').stickyTabs();

    $('#resultNavTabs a').click(function (e) {
          e.preventDefault()
          $(this).tab('show')
    });

    $('button#delete-result').click(function (e) {
        e.preventDefault()
        $.ajax({
           type: "DELETE",
           url: "/result/" + end[2],
           success: function (data){ window.location.href = "/search";},
           error:function(){
               alert("Something went wrong.");
           }
        });
    });

    $('button#reimport-result').click(function (e) {
        e.preventDefault()
        button = document.getElementById("reimport-result")
        button.disabled = true;
        currurl = window.location.href;
        $.ajax({
           type: "PUT",
           url: "/result/" + end[2],
           success: function (data){
              alert("Reimport complete");
              window.location.href = currurl;
           },
           error:function(){
               alert("Something went wrong.");
           }
        });
    });

    $('a[href="#settings-filtered"]').click(function (e) {
      e.preventDefault();
      $("tr.default-value").remove();
    });
}

/*
 * Colorate the result table cells for the compare view
 */
function colorateCells() {
    table.cells().every( function () {
      // determine if tooltip is string or number
      var element = $(this.node())[0];
      if (element.attributes["title"] !== undefined) {
          // these are the compare values, one value or many separated by '\n'.
          // currently we only do this for one compare value
          var other_values_str = element.attributes["title"].value;
          var values = Array(element.textContent);
          Array.prototype.push.apply(values, other_values_str.split("\n"));
          var rgb;
          if (element.attributes["invert"] !== undefined) {
            rgb = getRGB(element.attributes["class"].value, values, true);
          } else {
            rgb = getRGB(element.attributes["class"].value, values, false);
          }
          if (rgb) {
            element.style.backgroundColor = "rgb(" + rgb.getColorString() + ")";
          }
      }
  })
}

/*
 * Get an array of values, and translate that to into an RGB array.
 */
function getRGB(valclass, arr_values, invert) {
  var contains_floats = false;
  var floatValues = Array();
  for (var i = 0; i < arr_values.length; i++) {
    var floatVal = parseFloat(arr_values[i]);
    if (!isNaN(floatVal)) {
      contains_floats = true;
      floatValues.push(floatVal);
    }
  }
  // if array is all floats
  if (floatValues.length === arr_values.length) {
    if (floatValues.allValuesSame()) {
      // all values the same, no color needed
      return null;
    } else {
      // compute the appropriate color
      return computeRGB(valclass, floatValues, invert);
    }
  } else if (arr_values.allValuesSame()) {
      return null;
  } else {
    // mix of floats and strings, or different strings
    return gray;
  }
}

function computeRGB(valclass, arr_values, invert) {
  console.log("valclass", valclass);
  // The first value of arr_values is the principle value for compare view

  // compute mean of the compare values
  var sum = 0.0;
  var arr_length = arr_values.length;
  for( var i = 0; i < arr_length; i++ ) {
    if (valclass.includes("Time")) {
      arr_values[i] = arr_values[i]+1;
    } else if (valclass.includes("Nodes")) {
      arr_values[i] = arr_values[i]+100;
    }
    sum += arr_values[i];
  }
  var mean = sum/(arr_length);

  var sum_of_squares = 0.0;
  for( var i = 0; i < arr_length; i++ ){
    sum_of_squares += (arr_values[i]-mean) * (arr_values[i]-mean);
  }
  var variance = Math.sqrt(sum_of_squares/(arr_length));
  var percentage = variance/mean;

  var largest = Math.max(...arr_values.slice(1));
  var smallest = Math.min(...arr_values.slice(1));
  var value = arr_values[0];

  if ( (smallest < 0 && largest > 0) || smallest == 0 || largest == 0) {
    return Interpolate(dark_gray, percentage);
  }

  if (invert) {
    var tmp = smallest;
    smallest = - largest;
    largest = - tmp;
    value = - value;
  }

  if (value < smallest) {
      percentage = (smallest - value)/smallest;
  } else if (value > largest) {
      percentage = (value - smallest)/smallest;
  }
  if (largest < value) {
    return Interpolate(red, percentage);
  } else if (smallest > value) {
    return Interpolate(green, percentage);
  } else {
    return Interpolate(dark_gray, percentage);
  }
}

function Interpolate(colorBase, percentage) {
  if (percentage >= 1) {
    return colorBase;
  }
  else {
    percentage = percentage * 100;
    if (percentage < 7) {
        percentage = 7;
    }
    var end_color = colorBase.getColors();
    var r = interpolate(255, end_color.r, 100, percentage);
    var g = interpolate(255, end_color.g, 100, percentage);
    var b = interpolate(255, end_color.b, 100, percentage);
    return new Color(r, g, b);
  }
}

// does math
function interpolate(start, end, steps, count) {
  var s = start,
      e = end,
      final = s + (((e - s) / steps) * count);
  return Math.floor(final);
}

// Class to manage an rgb color
function Color(_r, _g, _b) {
    var r, g, b;
    var setColors = function(_r, _g, _b) {
        r = _r;
        g = _g;
        b = _b;
    };

    setColors(_r, _g, _b);
    this.getColors = function() {
        var colors = {
            r: r,
            g: g,
            b: b
        };
        return colors;
    };

    this.getColorString = function() {
        return r + "," + g + "," + b;
    };
}
