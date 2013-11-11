
var width = 750,
    height = 300;

var color = d3.scale.category20();

var zoomInit = d3.behavior.zoom().translate([50,150]).scale(.8);

var force = d3.layout.force()
    .charge(-120)
    .linkDistance(30)
    .size([width, height]);

var svg = d3.select("#diagram-1").append("svg")
    .attr("width", width)
    .attr("height", height)
    //.append("g")
    .call(d3.behavior.zoom().on("zoom", zoom))
        .on("dblclick.zoom", null)
        .append("g")
    
  force
      .nodes(graph.nodes)
      .links(graph.links)
      .start();

  var link = svg.selectAll(".link")
      .data(graph.links)
      //.call(d3.behavior.zoom().scaleExtent([1, 8]).on("zoom", zoom)).on("dblclick.zoom", null)
    .enter().append("line")
      .attr("class", "link")
      .style("stroke-width", function(d) { return Math.sqrt(d.value); });

  var node = svg.selectAll(".node")
      .data(graph.nodes)
      //.call(d3.behavior.zoom().scaleExtent([1, 8]).on("zoom", zoom)).on("dblclick.zoom", null)
    .enter().append("circle")
      .attr("class", "node")
      .attr("r", function(d) { 
            if (d.group == 'Remind') {
               if (d.relateds == 0) return Math.sqrt(100)
               else return (d.relateds > 5) ? Math.sqrt(5*100) : Math.sqrt(d.relateds*100);
            }
            else if(d.group == 'Tag') return (d.relateds > 11) ? Math.sqrt(11*35) : Math.sqrt(d.relateds*35)
            else  return Math.sqrt(20)   
            })
      .style("fill", function(d) { return color(d.group); })
      .on("click", function(d,e) {
           e.defaultPrevented
           //console.log($('#'+d.name));
           var obj = $('#'+d.name)
           if (obj.attr('data')=='rem') highlight = 'highlight-blue' //'rgb(31, 119, 180)'
           if (obj.attr('data')=='tag') highlight = 'highlight-orange' //'rgb(255, 127, 14)'
           if (obj.attr('highlight') == 'true') { obj.removeClass(highlight);obj.attr('highlight', 'false');}
           else { obj.addClass(highlight).fadeIn(3800); obj.attr('highlight', 'true');if(!isOnScreen(obj)) obj.scrollTo(500);}
           
           })
      .call(force.drag);

  node.append("title")
      .text(function(d) { return d.name; });

  force.on("tick", function() {
    link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node.attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
  });
  
  function zoom() {
  //console.log("here", d3.event.translate, d3.event.scale);
   svg.attr("transform", "translate(" + d3.event.translate + ")scale(" + d3.event.scale + ")");
}

function isOnScreen(element)
{
    var curPos = element.offset();
    var curTop = curPos.top;
    var screenHeight = $(window).height();
    return (curTop > screenHeight) ? false : true;
}

jQuery.fn.extend(
{
  scrollTo : function(speed, easing)
  {
    return this.each(function()
    {
      var targetOffset = $(this).offset().top;
      $('html,body').animate({scrollTop: targetOffset - height}, speed, easing);
    });
  }
});
