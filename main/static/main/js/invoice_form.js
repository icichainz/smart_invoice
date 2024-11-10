document.addEventListener('DOMContentLoaded',()=>{

    // handle client informations elements change.
    const editableElements = document.querySelectorAll('[data-editable="true"]');
    
    editableElements.forEach(element => {
        element.addEventListener('click', () => {
            if (!element.querySelector('input')) {
                const inputField = document.createElement('input');
                inputField.type = 'text';
                inputField.value = element.textContent;
                inputField.className = 'input-edit';

                // Replace the element with the input field
                element.innerHTML = '';
                element.appendChild(inputField);
                inputField.focus();

                // Save changes on blur
                inputField.addEventListener('blur', () => saveChanges(inputField.value, element));
                // Save changes on Enter key
                inputField.addEventListener('keypress', (e) => {
                    if (e.key === 'Enter') {
                        saveChanges(inputField.value, element);
                    }
                });
            }
        });
    });

    function saveChanges(value, element ) {
        element.textContent = value;
        // Update the element's text content
       if (element.textContent.length === 0) {
          const nextElementSibling = element.nextElementSibling ;
          if (nextElementSibling && nextElementSibling.tagName === 'BR') {
            nextElementSibling.remove() ;
          }
          element.remove();
          return ;
       }
       

    }






})