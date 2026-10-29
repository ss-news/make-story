import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const source=await readFile(new URL('../model.js',import.meta.url),'utf8');
const {defaults,validate,worldPoint,movePivot,posed}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
const original=defaults();assert.deepEqual(validate(JSON.parse(JSON.stringify(original))),original);
const p=original.parts.find(p=>p.id==='head');p.rotation=34;
const before=worldPoint(p,0,0);movePivot(p,.2,.7);const after=worldPoint(p,0,0);
assert.ok(Math.hypot(before.x-after.x,before.y-after.y)<1e-9,'Moving pivot must preserve artwork position');
for(const bad of [NaN,Infinity,-1]){const d=defaults();d.parts[0].width=bad;assert.throws(()=>validate(d));}
assert.throws(()=>validate({...defaults(),parts:[{...defaults().parts[0],asset:'../../file'}]}));
const unchanged=JSON.stringify(original);const aiming=posed(original,'aim');assert.equal(JSON.stringify(original),unchanged,'Preview must not mutate source');assert.notDeepEqual(aiming,original);
for(const name of ['aim','scared','walk'])validate(posed(defaults(),name,1.3));
console.log('Model: roundtrip, pivot invariance, validation and non-destructive presets passed.');
