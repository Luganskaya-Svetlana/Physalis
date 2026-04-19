'use strict';

{
    document.addEventListener('DOMContentLoaded', () => {
        const deleteLink = document.querySelector('.submit-row .deletelink');
        if (deleteLink) {
            deleteLink.textContent = 'Удалить задачу';
        }
    });
}
