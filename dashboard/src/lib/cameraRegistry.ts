// Identities come exclusively from the shared backend registry. Unknown or
// ambiguous aliases never authorize an overlay (including two cameras on one source).
export type RegisteredCamera={camera_id:string;camera_name?:string;aliases?:string[]};
let cameras:RegisteredCamera[]=[];
const key=(value:unknown)=>typeof value==='string'?value.trim().toLowerCase().replace(/[\s-]+/g,'_'):'';
export function registerCameras(rows:RegisteredCamera[]){cameras=rows.filter(row=>typeof row.camera_id==='string');}
export function canonicalCameraId(value:unknown):string|null {
 const wanted=key(value);if(!wanted)return null;
 const matches=cameras.filter(row=>[row.camera_id,row.camera_name,...(row.aliases||[])].some(alias=>key(alias)===wanted));
 const ids=[...new Set(matches.map(row=>row.camera_id))];return ids.length===1?ids[0]:null;
}
export function sameCamera(a:unknown,b:unknown):boolean {
 const first=canonicalCameraId(a);return first!==null&&first===canonicalCameraId(b);
}
