const CD={
  4:{n:"Afghanistan",s:2,w:22,e:18},8:{n:"Albania",s:65,w:82,e:76},
  12:{n:"Algeria",s:52,w:79,e:64},24:{n:"Angola",s:42,w:41,e:38},
  32:{n:"Argentina",s:58,w:91,e:78},36:{n:"Australia",s:87,w:99,e:95},
  40:{n:"Austria",s:91,w:99,e:93},50:{n:"Bangladesh",s:45,w:58,e:48},
  56:{n:"Belgium",s:84,w:99,e:92},64:{n:"Bhutan",s:70,w:72,e:62},
  68:{n:"Bolivia",s:55,w:68,e:66},76:{n:"Brazil",s:48,w:87,e:72},
  104:{n:"Myanmar",s:18,w:48,e:42},116:{n:"Cambodia",s:52,w:61,e:53},
  120:{n:"Cameroon",s:38,w:42,e:43},124:{n:"Canada",s:88,w:99,e:94},
  140:{n:"Central African Rep.",s:8,w:15,e:12},144:{n:"Sri Lanka",s:55,w:80,e:71},
  152:{n:"Chile",s:72,w:91,e:83},156:{n:"China",s:62,w:86,e:74},
  170:{n:"Colombia",s:48,w:88,e:72},180:{n:"DR Congo",s:10,w:21,e:18},
  188:{n:"Costa Rica",s:74,w:92,e:80},192:{n:"Cuba",s:68,w:92,e:86},
  218:{n:"Ecuador",s:44,w:86,e:74},818:{n:"Egypt",s:48,w:82,e:61},
  231:{n:"Ethiopia",s:32,w:28,e:35},246:{n:"Finland",s:92,w:99,e:94},
  250:{n:"France",s:82,w:99,e:91},276:{n:"Germany",s:88,w:99,e:94},
  288:{n:"Ghana",s:58,w:58,e:58},300:{n:"Greece",s:72,w:99,e:86},
  320:{n:"Guatemala",s:38,w:78,e:60},324:{n:"Guinea",s:32,w:28,e:22},
  340:{n:"Honduras",s:35,w:79,e:60},356:{n:"India",s:52,w:68,e:58},
  360:{n:"Indonesia",s:58,w:72,e:62},364:{n:"Iran",s:42,w:88,e:68},
  368:{n:"Iraq",s:28,w:72,e:48},372:{n:"Ireland",s:92,w:99,e:94},
  376:{n:"Israel",s:38,w:99,e:90},380:{n:"Italy",s:80,w:99,e:89},
  392:{n:"Japan",s:88,w:99,e:93},400:{n:"Jordan",s:55,w:88,e:72},
  404:{n:"Kenya",s:42,w:42,e:52},408:{n:"North Korea",s:15,w:72,e:68},
  410:{n:"South Korea",s:82,w:99,e:93},418:{n:"Laos",s:58,w:58,e:50},
  422:{n:"Lebanon",s:32,w:62,e:72},430:{n:"Liberia",s:38,w:28,e:30},
  434:{n:"Libya",s:22,w:58,e:52},450:{n:"Madagascar",s:48,w:22,e:32},
  454:{n:"Malawi",s:52,w:48,e:42},458:{n:"Malaysia",s:70,w:92,e:78},
  484:{n:"Mexico",s:42,w:92,e:74},496:{n:"Mongolia",s:68,w:72,e:68},
  504:{n:"Morocco",s:58,w:78,e:58},508:{n:"Mozambique",s:35,w:28,e:28},
  516:{n:"Namibia",s:62,w:72,e:68},524:{n:"Nepal",s:55,w:62,e:52},
  528:{n:"Netherlands",s:88,w:99,e:93},554:{n:"New Zealand",s:90,w:99,e:95},
  566:{n:"Nigeria",s:28,w:38,e:38},578:{n:"Norway",s:92,w:99,e:95},
  586:{n:"Pakistan",s:32,w:52,e:38},604:{n:"Peru",s:52,w:82,e:72},
  608:{n:"Philippines",s:48,w:72,e:68},616:{n:"Poland",s:72,w:99,e:88},
  620:{n:"Portugal",s:88,w:99,e:88},642:{n:"Romania",s:68,w:82,e:80},
  643:{n:"Russia",s:18,w:88,e:82},646:{n:"Rwanda",s:58,w:52,e:55},
  682:{n:"Saudi Arabia",s:52,w:92,e:72},686:{n:"Senegal",s:52,w:42,e:42},
  694:{n:"Sierra Leone",s:42,w:28,e:30},706:{n:"Somalia",s:5,w:15,e:10},
  710:{n:"South Africa",s:48,w:72,e:72},716:{n:"Zimbabwe",s:38,w:52,e:52},
  724:{n:"Spain",s:84,w:99,e:91},729:{n:"Sudan",s:12,w:38,e:32},
  752:{n:"Sweden",s:90,w:99,e:94},756:{n:"Switzerland",s:90,w:99,e:94},
  760:{n:"Syria",s:8,w:38,e:38},764:{n:"Thailand",s:62,w:88,e:72},
  788:{n:"Tunisia",s:58,w:82,e:70},792:{n:"Turkey",s:48,w:88,e:74},
  800:{n:"Uganda",s:40,w:42,e:42},804:{n:"Ukraine",s:15,w:88,e:84},
  826:{n:"United Kingdom",s:84,w:99,e:93},840:{n:"United States",s:72,w:99,e:92},
  858:{n:"Uruguay",s:78,w:92,e:82},862:{n:"Venezuela",s:28,w:72,e:68},
  887:{n:"Yemen",s:5,w:25,e:30},894:{n:"Zambia",s:52,w:48,e:52}
};

(function(){
var DIMS={s:{l:"Security",n:"Security score: intended to follow the Global Peace Index 2025, inverted and normalised to 0 to 100. Approximate, hand-entered."},
 w:{l:"Water",n:"Water score: intended to follow the WHO/UNICEF JMP 2024 share of population with safely managed drinking water. Approximate, hand-entered. Note that access to a service does not show whether it keeps working."},
 e:{l:"Education",n:"Education score: intended to follow the UNDP Education Index 2022 on a 0 to 100 scale. Approximate, hand-entered. It does not measure learning."}};
var cur='s';
function bin(v){return v>=80?5:v>=65?4:v>=50?3:v>=35?2:1}
function css(n){return getComputedStyle(document.documentElement).getPropertyValue(n).trim()}
function paint(){
  var unk=css('--unk');
  document.querySelectorAll('#world-g path').forEach(function(p){
    var d=CD[+p.getAttribute('data-id')];
    p.setAttribute('fill',d?css('--m'+bin(d[cur])):unk);
  });
  document.getElementById('note').textContent=DIMS[cur].n;
}
document.querySelectorAll('.mtab').forEach(function(b){b.addEventListener('click',function(){
  cur=b.dataset.dim;
  document.querySelectorAll('.mtab').forEach(function(x){var on=x===b;x.classList.toggle('on',on);x.setAttribute('aria-selected',on)});
  paint();
})});
fetch('world-110m.json').then(function(r){return r.json()}).then(function(world){
  var svg=d3.select('#world-svg'),proj=d3.geoNaturalEarth1().scale(140).translate([450,230]),path=d3.geoPath(proj);
  svg.select('#world-g').selectAll('path').data(topojson.feature(world,world.objects.countries).features).join('path')
   .attr('data-id',function(d){return d.id}).attr('d',path).attr('stroke',css('--bg')).attr('stroke-width',0.4)
   .on('mousemove',function(ev,d){
     var c=CD[+d.id],tt=document.getElementById('tt'),box=document.querySelector('.mapbox').getBoundingClientRect();
     if(!c){tt.hidden=true;return}
     document.getElementById('tt-n').textContent=c.n;
     document.getElementById('tt-d').textContent=DIMS[cur].l+':';
     document.getElementById('tt-v').textContent=c[cur]+' (approx.)';
     tt.hidden=false;
     var x=ev.clientX-box.left+12,y=ev.clientY-box.top+12;
     tt.style.left=Math.min(x,box.width-tt.offsetWidth-4)+'px';tt.style.top=y+'px';})
   .on('mouseleave',function(){document.getElementById('tt').hidden=true});
  svg.style('background',css('--sea'));
  paint();
}).catch(function(){document.getElementById('note').textContent='The map data could not be loaded.'});
matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(){setTimeout(paint,50)});
})();
