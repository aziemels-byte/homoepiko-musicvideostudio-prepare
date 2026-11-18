// Drop-in art direction sketch for makevoid's Anim p5 environment.
// Generates ONLY a 2.5D/graphic world plate. Put isolated dance footage above it.
// Timing is frame based; adapt segment boundaries after MVD audio analysis.
Anim.sketch({
  draw(t, frame) {
    const bpm=136, beat=(t*bpm/60), hit=Math.exp(-6*(beat-Math.floor(beat)));
    randomSeed(1200+Math.floor(frame/5));
    background(18,21,36);
    push(); translate(width/2,height/2);
    const city=(t<70), paint=(t>=70&&t<140), lilliput=(t>=140);
    const zoom=1+0.015*hit;
    scale(zoom);
    // Every arm/chest "hit" should be correlated with real motion cues in editorial pass.
    for(let i=-8;i<=8;i++) {
      const x=i*140;
      const a=0.15*Math.sin(t*.4+i*.7);
      push(); translate(x,0); rotate(a+hit*.025);
      noStroke();
      const h=city?450+100*Math.sin(i*.9+t*.3):paint?280+180*Math.sin(t*.6+i):180+90*Math.cos(i+t);
      fill((80+12*i+256)%256,58+80*hit,158+70*Math.sin(i+t));
      rect(-51,-h,102,h+850);
      pop();
    }
    noFill(); strokeWeight(2+7*hit);
    for(let j=0;j<17;j++) {
      const r=150+j*48+65*hit*Math.sin(j*1.4);
      stroke(235,95+j*6,190+j*2,95);
      push(); rotate(j*.16+t*.09); ellipse(0,0,r*2,r*(lilliput?.7:1.2)); pop();
    }
    // Graphic hatching echoes popping silhouettes, without creating fake people.
    stroke(255,165,65,110); strokeWeight(2);
    for(let k=0;k<50;k++) {
      const x=k*50-1200, y=220+30*Math.sin(k*.31+t*1.7);
      line(x,y,x+18+38*hit,y-22-60*hit);
    }
    pop();
  }
});
