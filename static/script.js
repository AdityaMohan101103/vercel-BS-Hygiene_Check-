document.getElementById('scrapeBtn').addEventListener('click', function() {
    const url = document.getElementById('url').value;
    fetch('/get_menu', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ url: url })
    })
    .then(response => response.json())
    .then(data => {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '';
        if (data.error) {
            resultDiv.innerHTML = `<p style="color: red;">${data.error}</p>`;
        } else {
            const ul = document.createElement('ul');
            data.forEach(item => {
                const li = document.createElement('li');
                li.textContent = `${item.item_name} - ${item.price}`;
                ul.appendChild(li);
            });
            resultDiv.appendChild(ul);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});
