const assert=require('node:assert/strict'),W=require('../static/walls.js');
const width=160,height=120,data=new Uint8ClampedArray(width*height*4).fill(255);
function dot(x,y){let i=(y*width+x)*4;data[i]=data[i+1]=data[i+2]=0;}
for(let x=20;x<=140;x++){dot(x,20);dot(x,100);}for(let y=20;y<=100;y++){dot(20,y);dot(140,y);}for(let x=50;x<56;x++)dot(x,50);
const walls=W.detect(data,width,height);assert.ok(walls.length>=4);const hit=W.nearest([80,22],walls);assert.ok(hit.distance<3);assert.ok(Math.abs(Math.sin(hit.wall.angle))<.04);assert.ok(!walls.some(w=>w.length<35));assert.deepEqual(W.detect(new Uint8ClampedArray(width*height*4).fill(255),width,height),[]);console.log('PASS wall detection, nearest-wall snapping, text-stroke rejection, blank image');
