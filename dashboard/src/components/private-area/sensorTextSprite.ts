import * as THREE from 'three';
// Adapted from threejs_test/main.js createTextSprite/updateSpriteText.
// One texture per schematic fixture, created once and disposed with the room.
export function createSensorTextSprite(text:string) {
 const canvas=document.createElement('canvas');canvas.width=320;canvas.height=80;
 const context=canvas.getContext('2d');
 if(!context)throw new Error('Sensor label canvas unavailable');
 context.fillStyle='rgba(255,255,255,0.95)';context.fillRect(0,0,canvas.width,canvas.height);
 context.fillStyle='#0f172a';context.font='bold 24px sans-serif';context.textAlign='center';context.textBaseline='middle';context.fillText(text,160,40);
 const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;
 const sprite=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,transparent:true,depthTest:false}));
 sprite.scale.set(1.65,0.42,1);sprite.renderOrder=5;
 return sprite;
}
