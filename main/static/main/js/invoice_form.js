document.addEventListener('DOMContentLoaded',()=>{
    const editableInvoiceid = document.getElementById('invoice-num-id');
    let editableInvoiceIdInpput;

    const editableInvoiceClientEls= document.querySelectorAll('[data-editable="true"]') ;

    // hanle edition features related to invoice number.
    editableInvoiceid.addEventListener('click',(e)=>{
        console.log('Invoice number clicked') ;
        if (!editableInvoiceIdInpput) {
            editableInvoiceIdInpput = document.createElement('input');
            editableInvoiceIdInpput.type = 'text';
            editableInvoiceIdInpput.value = editableInvoiceid.textContent;
            editableInvoiceIdInpput.className = 'input-edit';


            // Replace the div with the input field
           editableInvoiceid.innerHTML = '';
           editableInvoiceid.appendChild(editableInvoiceIdInpput);
            editableInvoiceIdInpput.focus();

            // Handle focus out
            editableInvoiceIdInpput.addEventListener('blur', () => {
               editableInvoiceid.textContent = editableInvoiceIdInpput.value;
                editableInvoiceIdInpput = null; // Clear editableInvoiceIdInpput reference
            });

            // Handle Enter key
            editableInvoiceIdInpput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                   editableInvoiceid.textContent = editableInvoiceIdInpput.value;
                    editableInvoiceIdInpput = null; // Clear editableInvoiceIdInpput reference
                }
            });
        }
    });


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

    function saveChanges(value, element) {
        // Update the element's text content
        element.textContent = value;

    }



})