// modal teacher
document.addEventListener('DOMContentLoaded',function(){
  const modal=document.querySelector('.teacher-modal');
  if(!modal) return;
  const modalImg=modal.querySelector('.modal-img');
  const modalText=modal.querySelector('.modal-text');
  const closeBtn=modal.querySelector('.modal-close');
  const cards=document.querySelectorAll('.teacher-card');

  function open(details){
    const img=details.querySelector('img');
    const box=details.querySelector('div');
    if(img) modalImg.src=img.src; else modalImg.removeAttribute('src');
    modalText.innerHTML=box?box.innerHTML:'';
    modal.classList.add('open');
    document.body.classList.add('no-scroll');
  }
  function close(){
    modal.classList.remove('open');
    document.body.classList.remove('no-scroll');
  }

  cards.forEach(card=>{
    card.addEventListener('click',()=>{
      const details=document.getElementById('teacher-'+card.dataset.name);
      if(details) open(details);
    });
  });

  closeBtn&&closeBtn.addEventListener('click',close);
  modal.addEventListener('click',e=>{ if(e.target===modal) close(); });
  document.addEventListener('keydown',e=>{ if(e.key==='Escape'&&modal.classList.contains('open')) close(); });
});
