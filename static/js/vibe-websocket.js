(function(){
  async function wait(ms){ return new Promise(resolve=>setTimeout(resolve, ms)); }
  async function pollStatus(taskId, onMessage){
    while(true){
      const response=await fetch(`/vibe/status/${taskId}`);
      const payload=await response.json();
      onMessage(payload);
      if(['completed','completed_with_errors','failed'].includes(payload.status)) return;
      await wait(500);
    }
  }

  function connectVibe(taskId, onMessage){
    const protocol=location.protocol==='https:'?'wss':'ws';
    try {
      const socket=new WebSocket(`${protocol}://${location.host}/vibe/updates/${taskId}`);
      socket.onmessage=(event)=>onMessage(JSON.parse(event.data));
      socket.onerror=()=>pollStatus(taskId, onMessage);
      return socket;
    } catch (error) {
      pollStatus(taskId, onMessage);
      return null;
    }
  }
  window.connectVibe=connectVibe;
})();
