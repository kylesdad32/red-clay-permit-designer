/* Building-aligned geometry, independent of image coordinates. */
(function(root){
 const local=(p,a)=>[p[0]*Math.cos(a)+p[1]*Math.sin(a),-p[0]*Math.sin(a)+p[1]*Math.cos(a)];
 const world=(p,a)=>[p[0]*Math.cos(a)-p[1]*Math.sin(a),p[0]*Math.sin(a)+p[1]*Math.cos(a)];
 function predict(p,points,a,tolerance=14){
  if(!points.length)return {point:p,label:'First corner'};
  const q=local(p,a),last=local(points.at(-1),a),first=local(points[0],a);
  let axis=Math.abs(q[0]-last[0])>=Math.abs(q[1]-last[1])?0:1;
  q[1-axis]=last[1-axis];
  let label=axis===0?'Parallel to wall':'Square to wall';
  if(points.length>=3&&Math.abs(q[axis]-first[axis])<tolerance){q[axis]=first[axis];label='Aligned with first corner';}
  return {point:world(q,a),label};
 }
 function move(points,index,p,a,square=true){
  const out=points.map(x=>x.slice());
  if(!square||points.length<3){out[index]=p;return out;}
  const coords=points.map(x=>local(x,a)),old=coords[index],next=local(p,a);
  for(const j of [(index+points.length-1)%points.length,(index+1)%points.length]){
   const v=coords[j];
   if(Math.abs(v[0]-old[0])<0.01)v[0]=next[0];
   else if(Math.abs(v[1]-old[1])<0.01)v[1]=next[1];
  }
  coords[index]=next;return coords.map(x=>world(x,a));
 }
 const api={local,world,predict,move};if(typeof module!=='undefined')module.exports=api;root.RedClayGeometry=api;
})(typeof window!=='undefined'?window:globalThis);
