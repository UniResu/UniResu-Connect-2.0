document.addEventListener('DOMContentLoaded', () => {
    const openModalBtn = document.getElementById('openModalBtn');
    const closeModalBtn = document.getElementById('closeModalBtn');
    const modalOverlay = document.getElementById('editProfileModal');
    const editProfileForm = document.getElementById('editProfileForm');

    const profileCourse = document.getElementById('profileCourseValue');
    const profilePeriod = document.getElementById('profilePeriodValue');
    const profileDegree = document.getElementById('profileDegreeValue');

    const summaryDisplay = document.getElementById('profileSummaryText');
    const summaryTextarea = document.getElementById('professionalSummaryTextarea');
    const saveSummaryBtn = document.getElementById('saveSummaryBtn');

    const openModal = () => {
        if (modalOverlay) modalOverlay.style.display = 'flex';
    };
    const closeModal = () => {
        if (modalOverlay) modalOverlay.style.display = 'none';
    };

    if (openModalBtn) {
        openModalBtn.addEventListener('click', openModal);
    } else {
        console.error("Erro: Botão de abrir modal (id='openModalBtn') não encontrado.");
    }
    if (closeModalBtn) closeModalBtn.addEventListener('click', closeModal);
    if (modalOverlay) {
        modalOverlay.addEventListener('click', (event) => {
            if (event.target === modalOverlay) closeModal();
        });
    }

    if (summaryDisplay && summaryTextarea && saveSummaryBtn) {
        summaryDisplay.addEventListener('click', () => {
            summaryTextarea.value = summaryDisplay.textContent.trim();
            summaryDisplay.style.display = 'none';
            summaryTextarea.style.display = 'block';
            saveSummaryBtn.style.display = 'block';
            summaryTextarea.focus();
        });
        saveSummaryBtn.addEventListener('click', () => {
            summaryDisplay.textContent = summaryTextarea.value;
            summaryTextarea.style.display = 'none';
            saveSummaryBtn.style.display = 'none';
            summaryDisplay.style.display = 'block';
        });
    }

    if (editProfileForm) {
        editProfileForm.addEventListener('submit', (event) => {
            event.preventDefault();
            const newCourse = document.getElementById('editCourse').value;
            const newPeriod = document.getElementById('editPeriod').value;
            const newDegree = document.getElementById('editDegree').value;
            if (profileCourse) profileCourse.textContent = newCourse;
            if (profilePeriod) profilePeriod.textContent = newPeriod;
            if (profileDegree) profileDegree.textContent = newDegree;
            closeModal();
            alert('Informações atualizadas com sucesso!');
        });
    } else {
         console.error("Erro: Formulário do modal (id='editProfileForm') não encontrado.");
    }

    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('cv-upload');
    const uploadFeedback = uploadArea ? uploadArea.querySelector('.upload-feedback') : null;
    
    if (uploadArea && fileInput && uploadFeedback) {
        const originalUploadHTML = uploadFeedback.innerHTML;
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, preventDefaults, false);
        });
        function preventDefaults(e) { e.preventDefault(); e.stopPropagation(); }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('drag-over'), false);
        });
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('drag-over'), false);
        });

        uploadArea.addEventListener('drop', handleDrop, false);
        function handleDrop(e) {
            const files = e.dataTransfer.files;
            if (files.length > 0) handleFile(files[0]);
        }

        uploadArea.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) handleFile(this.files[0]);
        });

        function handleFile(file) {
            const allowedTypes = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'];
            if (file && allowedTypes.includes(file.type)) {
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                uploadFeedback.innerHTML = `<i class="fas fa-file-check" style="color: #2ecc71;"></i><span>${file.name}</span>`;
            } else {
                alert('Tipo de arquivo não suportado. Por favor, anexe um PDF ou DOCX.');
                uploadFeedback.innerHTML = originalUploadHTML;
                fileInput.value = '';
            }
        }
    } else {
        console.warn("Aviso: Componentes de upload (id='uploadArea') não encontrados nesta página.");
    }
});