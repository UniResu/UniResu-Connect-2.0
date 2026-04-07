document.addEventListener('DOMContentLoaded', () => {

    const API_BASE_URL = 'http://127.0.0.1:8000';
    const searchForm = document.getElementById('form-busca');
    const projectListContainer = document.getElementById('lista-projetos');

    loadInitialProjects();

    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }

    async function handleSearch(event) {
        event.preventDefault(); 

        const buscar = document.getElementById('input-buscar').value;
        const local = document.getElementById('input-local').value;
        const area = document.getElementById('select-area').value;
        const remoto = document.getElementById('check-remoto').checked;
        const tipoCheckboxes = document.querySelectorAll('input[name="tipo_projeto"]:checked');
        const tipos = Array.from(tipoCheckboxes).map(cb => cb.value);

        const params = new URLSearchParams();
        if (buscar) params.append('q', buscar);
        if (local) params.append('local', local);
        if (area) params.append('area', area);
        if (remoto) params.append('remoto', 'true');
        if (tipos.length > 0) params.append('tipos', tipos.join(','));

        const apiUrl = `${API_BASE_URL}/api/projetos/buscar?${params.toString()}`;

        fetchAndRenderProjects(apiUrl);
    }

    async function loadInitialProjects() {

        const apiUrl = `${API_BASE_URL}/api/projetos/buscar`;
        
        fetchAndRenderProjects(apiUrl);
    }

    async function fetchAndRenderProjects(apiUrl) {
        try {
            projectListContainer.innerHTML = '<p>Carregando projetos...</p>';
            const response = await fetch(apiUrl);

            if (!response.ok) {
                throw new Error(`Erro na rede: ${response.statusText}`);
            }

            const projetosFiltrados = await response.json();
            renderProjects(projetosFiltrados);

        } catch (error) {
            console.error('Falha ao buscar projetos:', error);
            projectListContainer.innerHTML = '<p class="error">Erro ao carregar projetos. Tente novamente mais tarde.</p>';
        }
    }

    function renderProjects(projects) {
        projectListContainer.innerHTML = '';

        if (!projects || projects.length === 0) {
            projectListContainer.innerHTML = '<p>Nenhum projeto encontrado com esses filtros.</p>';
            return;
        }

        projects.forEach(project => {
            const card = document.createElement('div');
            card.className = 'project-card';

            card.innerHTML = `
                <div class="project-info">
                    <h3>${project.titulo || 'Título não disponível'}</h3>
                    <p>${project.descricao || 'Sem descrição.'}</p>
                </div>
                <div class="project-meta">
                    <span class="institution">${project.instituicao || 'Instituição'}</span>
                    <span class="type">${project.tipo || 'Tipo'}</span>
                    <span class="date">${project.dataPublicacao || 'Data'}</span>
                </div>
            `;
            
            projectListContainer.appendChild(card);
        });
    }
});