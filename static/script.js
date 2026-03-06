const fileInput = document.getElementById('fileInput');
const fileCount = document.getElementById('file-count');
const roastBtn = document.getElementById('roastBtn');
const loading = document.getElementById('loading');
const resultArea = document.getElementById('resultArea');
const resultImage = document.getElementById('resultImage');
const downloadBtn = document.getElementById('downloadBtn');

fileInput.addEventListener('change', () => {
    const count = fileInput.files.length;
    fileCount.innerText = count > 0 ? `${count} files selected` : '';
});

roastBtn.addEventListener('click', async () => {
    if(fileInput.files.length === 0) {
        alert("Bhai, kam se kam ek screenshot toh upload kar!");
        return;
    }
    if(fileInput.files.length > 3) {
        alert("Jyada shana mat ban! Max 3 files allowed hain.");
        return;
    }

    // Hide Button, Show Loading
    roastBtn.classList.add('hidden');
    loading.classList.remove('hidden');
    resultArea.classList.add('hidden');

    const formData = new FormData();
    for(let i=0; i < fileInput.files.length; i++) {
        formData.append('files[]', fileInput.files[i]);
    }

    try {
        const response = await fetch('/roast', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if(data.success) {
            resultImage.src = data.image_url;
            downloadBtn.href = data.image_url;
            loading.classList.add('hidden');
            resultArea.classList.remove('hidden');
            roastBtn.classList.remove('hidden'); // Show button again to roast more
            roastBtn.innerText = "ROAST ANOTHER NOOB";
        } else {
            alert(data.error);
            loading.classList.add('hidden');
            roastBtn.classList.remove('hidden');
        }
    } catch (err) {
        alert("Kuch server mein gadbad ho gayi. Retry kar.");
        loading.classList.add('hidden');
        roastBtn.classList.remove('hidden');
    }
});