(function(){
var hero=document.querySelector(".i-hero");if(!hero)return;
if(matchMedia("(prefers-reduced-motion:reduce)").matches)return;
var iris=hero.querySelector(".i-iris"),wm=hero.querySelector(".i-wm"),hint=hero.querySelector(".i-hint"),
rs=[].slice.call(hero.querySelectorAll(".r")),bands=[].slice.call(document.querySelectorAll(".i-band")),gl=[].slice.call(document.querySelectorAll(".i-g"));
function cl(x,a,b){return Math.min(b===undefined?1:b,Math.max(a||0,x))}
function ease(t){return t*t*(3-2*t)}
var t=false;
function f(){t=false;var y=scrollY,vh=innerHeight,top=hero.getBoundingClientRect().top+y,p=cl((y-top)/(hero.offsetHeight-vh));
 rs.forEach(function(r,i){var s=1+Math.pow(p,1.6)*(2.2+i*1.7);r.style.transform="scale("+s+") rotate("+((i%2?-1:1)*p*70)+"deg)";r.style.opacity=cl(1-(p-.05)*(1.4+(rs.length-i)*.15))});
 wm.style.opacity=cl(1-p*4);wm.style.transform="translateY(-50%) scale("+(1+p*.8)+")";hint.style.opacity=cl(1-p*10);
 iris.style.clipPath="circle("+(ease(cl((p-.3)/.55))*150)+"% at 50% 50%)";
 bands.forEach(function(b){var r=b.getBoundingClientRect();b.style.transform="translateX("+((r.top-vh/2)*b.dataset.s)+"px)"});
 gl.forEach(function(g){var r=g.parentElement.getBoundingClientRect();g.style.transform="translateY("+((r.top+r.height/2-vh/2)*g.dataset.p)+"px) rotate("+((r.top-vh/2)*g.dataset.p*.05)+"deg)"})}
function q(){if(!t){t=true;requestAnimationFrame(f)}}
addEventListener("scroll",q,{passive:true});addEventListener("resize",q);f();
})();
