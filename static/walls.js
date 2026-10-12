/* Detect long dark line segments, excluding short text strokes. Coordinates are SVG units. */
(function(root){
 function detect(data,w,h,factor=1){
  const pixels=[];for(let y=0;y<h;y++)for(let x=0;x<w;x++){let i=(y*w+x)*4;if(data[i+3]>180&&Math.max(data[i],data[i+1],data[i+2])<100)pixels.push([x,y]);}
  if(pixels.length>45000)return [];
  const radius=Math.ceil(Math.hypot(w,h)),bins=radius*2+1,candidates=[];
  for(let deg=0;deg<180;deg++){
   const a=deg*Math.PI/180,c=Math.cos(a),s=Math.sin(a),votes=new Uint16Array(bins);
   for(const [x,y] of pixels)votes[Math.round(x*c+y*s)+radius]++;
   for(let r=0;r<bins;r++)if(votes[r]>=35)candidates.push({a,c,s,r:r-radius,v:votes[r]});
  }
  candidates.sort((a,b)=>b.v-a.v);const segments=[];
  for(const line of candidates.slice(0,140)){
   const pts=pixels.filter(([x,y])=>Math.abs(x*line.c+y*line.s-line.r)<0.8).map(([x,y])=>-x*line.s+y*line.c).sort((a,b)=>a-b);
   let start=0;for(let i=1;i<=pts.length;i++)if(i===pts.length||pts[i]-pts[i-1]>3){
    const lo=pts[start],hi=pts[i-1];if(hi-lo>=35&&i-start>=(hi-lo)*0.7){
     const a=[(line.r*line.c-lo*line.s)*factor,(line.r*line.s+lo*line.c)*factor],b=[(line.r*line.c-hi*line.s)*factor,(line.r*line.s+hi*line.c)*factor];
     const angle=Math.atan2(b[1]-a[1],b[0]-a[0]);
     if(!segments.some(seg=>Math.abs(Math.sin(seg.angle-angle))<0.04&&distance(a,seg).distance<5&&distance(b,seg).distance<5))segments.push({a,b,angle,length:(hi-lo)*factor});
    }start=i;
   }
  }
  return segments.sort((a,b)=>b.length-a.length).slice(0,70);
 }
 function distance(p,seg){const dx=seg.b[0]-seg.a[0],dy=seg.b[1]-seg.a[1],t=Math.max(0,Math.min(1,((p[0]-seg.a[0])*dx+(p[1]-seg.a[1])*dy)/(dx*dx+dy*dy)));const point=[seg.a[0]+t*dx,seg.a[1]+t*dy];return {distance:Math.hypot(p[0]-point[0],p[1]-point[1]),point,wall:seg};}
 function nearest(p,walls){return walls.map(w=>distance(p,w)).sort((a,b)=>a.distance-b.distance)[0]||null;}
 const api={detect,nearest};if(typeof module!=='undefined')module.exports=api;root.RedClayWalls=api;
})(typeof window!=='undefined'?window:globalThis);
