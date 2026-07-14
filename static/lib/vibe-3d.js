(function(){
  const COLORS={CRITICAL:'#ff3366',HIGH:'#ff7a00',MEDIUM:'#00ccff',LOW:'#00ff88'};
  const MIN_CANVAS_SIZE = 320;
  class VibeScene {
    constructor(canvas){
      this.canvas=canvas;
      this.ctx=canvas.getContext('2d');
      this.issues=[];
      this.agents=[];
      this.tick=0;
      this.resize();
      window.addEventListener('resize',()=>this.resize());
      requestAnimationFrame(()=>this.render());
    }
    resize(){
      const rect=this.canvas.getBoundingClientRect();
      this.canvas.width=Math.max(MIN_CANVAS_SIZE, rect.width);
      this.canvas.height=Math.max(MIN_CANVAS_SIZE, rect.height);
    }
    update(snapshot){
      const issues=(snapshot.scan&&snapshot.scan.issues)||[];
      this.issues=issues.slice(0,64).map((issue,index)=>({
        x:(index%8)+1,
        y:Math.floor(index/8)+1,
        z:(index%5)+1,
        radius:8+((issue.impact_score||1)*3),
        color:COLORS[issue.severity]||COLORS.LOW,
        issue
      }));
      this.agents=Object.values(snapshot.agent_results||{}).map((agent,index)=>({
        x:50+(index*80),
        y:60+((index%3)*40),
        label:agent.agent,
        status:agent.status
      }));
    }
    render(){
      this.tick+=0.016;
      const ctx=this.ctx;
      ctx.clearRect(0,0,this.canvas.width,this.canvas.height);
      const gradient=ctx.createLinearGradient(0,0,this.canvas.width,this.canvas.height);
      gradient.addColorStop(0,'#07111f');
      gradient.addColorStop(1,'#0f0320');
      ctx.fillStyle=gradient;
      ctx.fillRect(0,0,this.canvas.width,this.canvas.height);

      for(const issue of this.issues){
        const px=(issue.x/9)*this.canvas.width + Math.sin(this.tick+issue.z)*18;
        const py=(issue.y/9)*this.canvas.height + Math.cos(this.tick+issue.x)*18;
        ctx.beginPath();
        ctx.fillStyle=issue.color;
        ctx.shadowBlur=20;
        ctx.shadowColor=issue.color;
        ctx.arc(px,py,issue.radius,0,Math.PI*2);
        ctx.fill();
      }
      ctx.shadowBlur=0;

      for(const agent of this.agents){
        ctx.fillStyle='#ffffff';
        ctx.strokeStyle='#00ff88';
        ctx.lineWidth=2;
        ctx.beginPath();
        ctx.rect(agent.x,agent.y,42,24);
        ctx.stroke();
        ctx.fillText(agent.label, agent.x, agent.y-8);
      }
      requestAnimationFrame(()=>this.render());
    }
  }
  window.VibeScene=VibeScene;
})();
