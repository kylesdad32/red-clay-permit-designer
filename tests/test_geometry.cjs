const assert=require('node:assert/strict');const G=require('../static/geometry.js');
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-8,`${a} != ${b}`);
for(const angle of [0,Math.PI/6,-Math.PI/4]){
 const points=[[0,0],[100,0],[100,60],[0,60]].map(p=>G.world(p,angle));
 const next=G.local(G.predict(G.world([105,58],angle),points.slice(0,2),angle).point,angle);near(next[0],100);near(next[1],58);
 const closing=G.local(G.predict(G.world([4,60],angle),points.slice(0,3),angle).point,angle);near(closing[0],0);near(closing[1],60);
 const edited=G.move(points,2,G.world([130,90],angle),angle).map(p=>G.local(p,angle));
 for(let i=0;i<4;i++){const a=edited[i],b=edited[(i+1)%4];assert.ok(Math.abs(a[0]-b[0])<1e-8||Math.abs(a[1]-b[1])<1e-8);}
 near(edited[2][0],130);near(edited[2][1],90);near(edited[0][0],0);near(edited[0][1],0);
 const free=G.move(points,2,[37,29],angle,false);assert.deepEqual(free[2],[37,29]);assert.deepEqual(free[1],points[1]);
}
console.log('PASS: square predictions, closure alignment, rotated corner resizing, free-angle editing');
