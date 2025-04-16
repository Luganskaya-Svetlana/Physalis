document.addEventListener('DOMContentLoaded', () => {

  // Создание общего модального окна
  const modal = document.createElement('div');
  modal.classList.add('modal');
  modal.innerHTML = `
    <div class="modal-content">
      <span class="modal-close">&times;</span>
      <img class="modal-img" src="" alt="modal image">
      <div class="modal-text"></div>
    </div>
  `;
  document.body.appendChild(modal);

  const modalImg = modal.querySelector('.modal-img');
  const modalText = modal.querySelector('.modal-text');

  // Открытие модалки с отзывами
  document.querySelectorAll('.review-card img').forEach(img => {
    img.addEventListener('click', () => {
      modalImg.src = img.getAttribute('data-full');
      modalImg.style.display = 'block';
      modalText.innerHTML = '';
      modalText.style.display = 'none';
      modal.style.display = 'flex';
    });
  });

  // Открытие модалки с преподавателями
  document.querySelectorAll('.teacher-card').forEach(card => {
    card.addEventListener('click', () => {
      const teacherId = card.getAttribute('data-name');
      const teacherDetails = document.getElementById(`teacher-${teacherId}`);

      modalImg.src = teacherDetails.querySelector('img').src;
      modalImg.style.display = 'block';
      modalText.innerHTML = teacherDetails.querySelector('div').innerHTML;
      modalText.style.display = 'block';
      modal.style.display = 'flex';
    });
  });

  // Закрытие модалки
  modal.addEventListener('click', (e) => {
    if (e.target === modal || e.target.classList.contains('modal-close')) {
      modal.style.display = 'none';
    }
  });

  // FAQ
  document.querySelectorAll('.faq-question').forEach(button => {
    button.addEventListener('click', () => {
      const answer = button.nextElementSibling;
      answer.classList.toggle('hidden');
    });
  });

});
