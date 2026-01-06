(function(){
  const modal=document.createElement("div");
  modal.className="pp-modal";
  modal.innerHTML='<button class="close" type="button">Close</button><img alt="image"/>';
  document.body.appendChild(modal);
  const img=modal.querySelector("img");
  const closeBtn=modal.querySelector(".close");
  const close=()=>{ modal.classList.remove("on"); img.src=""; };
  closeBtn.addEventListener("click", close);
  modal.addEventListener("click",(e)=>{ if(e.target===modal) close(); });
  document.addEventListener("keydown",(e)=>{ if(e.key==="Escape") close(); });

  document.querySelectorAll(".tip img.tipImg").forEach(t=>{
    t.addEventListener("click",()=>{
      img.src=t.dataset.full||t.src;
      modal.classList.add("on");
    });
  });

  async function del(btn){
    const tip=btn.closest(".tip");
    const id=tip?.dataset?.tipId;
    if(!id) return;
    if(!confirm("Delete this post?")) return;
    const r=await fetch("/api/delete?tip_id="+encodeURIComponent(id),{method:"POST"});
    const j=await r.json().catch(()=>({ok:false}));
    if(!j.ok){ alert(j.message||"Delete failed."); return; }
    tip.remove();
  }
  document.querySelectorAll("button.delbtn").forEach(b=>b.addEventListener("click",()=>del(b)));
})();
