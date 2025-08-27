class CartographyApp {
    constructor() {
        this.currentProject = null;
        this.currentJob = null;
        this.results = null;
        this.progressInterval = null;
        
        // Configuration pour déploiement avec base path
        this.basePath = window.location.pathname.replace(/\/$/, '').replace('/index.html', '') || '';
        this.apiBase = this.basePath + '/api/v1';
        
        console.log('🌐 Current URL:', window.location.href);
        console.log('🌐 Pathname:', window.location.pathname);
        console.log('🌐 BasePath:', this.basePath);
        console.log('🌐 API Base:', this.apiBase);
        
        this.initEventListeners();
    }
    
    initEventListeners() {
        // File uploads
        const pagesFile = document.getElementById('pages-file');
        const linksFile = document.getElementById('links-file');
        const analyzeBtn = document.getElementById('analyze-btn');
        
        console.log('🔌 Elements found:');
        console.log('📄 Pages file input:', pagesFile);
        console.log('🔗 Links file input:', linksFile);
        console.log('🚀 Analyze button:', analyzeBtn);
        
        if (pagesFile) {
            pagesFile.addEventListener('change', (e) => this.handleFileSelect(e, 'pages'));
            console.log('✅ Pages file listener attached');
        } else {
            console.error('❌ Pages file input not found!');
        }
        
        if (linksFile) {
            linksFile.addEventListener('change', (e) => this.handleFileSelect(e, 'links'));
            console.log('✅ Links file listener attached');
        } else {
            console.error('❌ Links file input not found!');
        }
        
        // Drag and drop
        this.setupDragAndDrop('pages-upload', pagesFile);
        this.setupDragAndDrop('links-upload', linksFile);
        
        // Analyze button
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.startAnalysis());
            console.log('✅ Analyze button listener attached');
        } else {
            console.error('❌ Analyze button not found!');
        }
        
        // Bouton test mock (ajouté temporairement)
        const testMockBtn = document.createElement('button');
        testMockBtn.textContent = '🎭 Test Mock Data';
        testMockBtn.className = 'test-mock-btn';
        testMockBtn.style.cssText = 'margin: 10px; padding: 10px 20px; background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer;';
        testMockBtn.addEventListener('click', () => this.loadMockData());
        document.querySelector('.upload-section').appendChild(testMockBtn);
    }
    
    setupDragAndDrop(uploadId, fileInput) {
        const uploadArea = document.getElementById(uploadId);
        
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, this.preventDefaults, false);
        });
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadArea.addEventListener(eventName, () => uploadArea.classList.remove('dragover'), false);
        });
        
        uploadArea.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                this.handleFileSelect({target: fileInput}, uploadId.includes('pages') ? 'pages' : 'links');
            }
        }, false);
    }
    
    preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }
    
    handleFileSelect(event, type) {
        const file = event.target.files[0];
        const uploadArea = document.getElementById(`${type}-upload`);
        
        console.log(`📁 File selected for ${type}:`, file ? file.name : 'none');
        
        if (file) {
            uploadArea.classList.add('file-selected');
            const icon = uploadArea.querySelector('.file-upload-icon');
            const title = uploadArea.querySelector('h3');
            
            icon.textContent = '✅';
            title.textContent = `${file.name}`;
        } else {
            uploadArea.classList.remove('file-selected');
            const icon = uploadArea.querySelector('.file-upload-icon');
            const title = uploadArea.querySelector('h3');
            
            icon.textContent = type === 'pages' ? '📄' : '🔗';
            title.textContent = type === 'pages' ? 'Fichier Pages' : 'Fichier Liens';
        }
        
        this.checkAnalyzeButtonState();
    }
    
    checkAnalyzeButtonState() {
        const pagesFile = document.getElementById('pages-file').files[0];
        const analyzeBtn = document.getElementById('analyze-btn');
        
        console.log('🔍 Checking analyze button state. Pages file:', pagesFile ? pagesFile.name : 'none');
        
        // Au minimum le fichier pages est requis
        analyzeBtn.disabled = !pagesFile;
        
        console.log('🔍 Analyze button disabled:', analyzeBtn.disabled);
    }
    
    async startAnalysis() {
        console.log('🎯 startAnalysis called!');
        console.log('🎯 Current project:', this.currentProject);
        
        // Récupérer les fichiers depuis le DOM
        const pagesFile = document.getElementById('pages-file').files[0];
        const linksFile = document.getElementById('links-file').files[0];
        
        console.log('🎯 Pages file:', pagesFile ? pagesFile.name : 'none');
        console.log('🎯 Links file:', linksFile ? linksFile.name : 'none');
        
        try {
            this.hideError();
            this.showProgress();
            
            // Étape 1: Créer un projet
            const project = await this.createProject();
            this.currentProject = project.id;
            
            // Étape 2: Upload des fichiers
            await this.uploadFiles();
            
            // Étape 3: Lancer l'analyse simple (sans Celery)
            this.updateProgress({ 
                status: 'Analyse en cours...', 
                progress_percentage: 0,
                step: 1,
                total_steps: 4,
                step_name: 'Démarrage de l\'analyse'
            });
            
            // Lancer l'analyse en arrière-plan et surveiller le progrès
            await this.startSimpleAnalysis();
            // Note: les résultats seront affichés automatiquement par le monitoring du progrès
            
        } catch (error) {
            console.error('Erreur:', error);
            this.showError(`Erreur lors de l'analyse: ${error.message}`);
            this.hideProgress();
        }
    }
    
    async createProject() {
        console.log('🚀 Creating project via:', `${this.apiBase}/projects/`);
        
        const response = await fetch(`${this.apiBase}/projects/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: `Analyse ${new Date().toLocaleString()}`,
                description: 'Analyse via interface web'
            })
        });
        
        console.log('📡 Create project response:', response.status, response.statusText);
        
        if (!response.ok) {
            throw new Error('Impossible de créer le projet');
        }
        
        return await response.json();
    }
    
    async uploadFiles() {
        const pagesFile = document.getElementById('pages-file').files[0];
        const linksFile = document.getElementById('links-file').files[0];
        
        this.updateProgress({ 
            status: 'Upload des fichiers...', 
            progress_percentage: 0,
            step: 1,
            total_steps: 4,
            step_name: 'Upload en cours'
        });
        
        // Upload du fichier pages par chunks
        await this.uploadFileByChunks(pagesFile, 'pages', 50);
        
        // Upload du fichier liens par chunks si présent
        if (linksFile) {
            await this.uploadFileByChunks(linksFile, 'links', 50);
        }
        
        // Finaliser l'import
        const response = await fetch(`${this.apiBase}/projects/${this.currentProject}/import-finalize`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'}
        });
        
        if (!response.ok) {
            throw new Error('Erreur lors de la finalisation de l\'upload');
        }
        
        return await response.json();
    }
    
    async uploadFileByChunks(file, fileType, progressStep = 50) {
        if (!file) return;
        
        console.log(`📁 Upload par chunks: ${file.name} (${file.size} bytes)`);
        
        const text = await file.text();
        const lines = text.split('\n');
        const header = lines[0];
        const dataLines = lines.slice(1).filter(line => line.trim());
        
        const chunkSize = 1000; // 1000 lignes par chunk
        const totalChunks = Math.ceil(dataLines.length / chunkSize);
        
        console.log(`📦 ${dataLines.length} lignes à uploader en ${totalChunks} chunks`);
        
        for (let i = 0; i < totalChunks; i++) {
            const start = i * chunkSize;
            const end = Math.min(start + chunkSize, dataLines.length);
            const chunkLines = dataLines.slice(start, end);
            
            // Reconstituer le CSV avec header
            const chunkCsv = header + '\n' + chunkLines.join('\n');
            const chunkBlob = new Blob([chunkCsv], { type: 'text/csv' });
            
            const formData = new FormData();
            formData.append('chunk_data', chunkBlob, `${fileType}_chunk_${i}.csv`);
            formData.append('file_type', fileType);
            formData.append('chunk_index', i.toString());
            formData.append('total_chunks', totalChunks.toString());
            formData.append('is_first_chunk', (i === 0).toString());
            formData.append('is_last_chunk', (i === totalChunks - 1).toString());
            
            const response = await fetch(`${this.apiBase}/projects/${this.currentProject}/import-chunk`, {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`Erreur upload chunk ${i + 1}/${totalChunks}`);
            }
            
            // Mise à jour du progrès
            const progress = Math.round((i + 1) / totalChunks * progressStep);
            this.updateProgress({ 
                status: `Upload ${fileType}: ${i + 1}/${totalChunks} chunks`, 
                progress_percentage: progress,
                step: 1,
                total_steps: 4,
                step_name: `Upload ${fileType}`
            });
            
            console.log(`✅ Chunk ${i + 1}/${totalChunks} uploadé`);
        }
        
        console.log(`🎉 Upload ${fileType} terminé: ${dataLines.length} lignes`);
    }
    
    async startSimpleAnalysis() {
        // Lancer l'analyse en arrière plan
        const response = await fetch(`${this.apiBase}/projects/${this.currentProject}/analyze-simple`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Erreur analyse: ${errorText}`);
        }
        
        // L'analyse est lancée, maintenant surveiller le progrès
        this.startProgressMonitoring();
        
        return await response.json();
    }
    
    startProgressMonitoring() {
        this.progressInterval = setInterval(async () => {
            try {
                const status = await this.getJobStatus();
                this.updateProgress(status);
                
                if (status.status === 'SUCCESS' || status.status === 'ANALYZED') {
                    clearInterval(this.progressInterval);
                    this.results = status.result;
                    this.showResults();
                } else if (status.status === 'FAILURE' || status.status === 'ERROR') {
                    clearInterval(this.progressInterval);
                    this.showError(`Analyse échouée: ${status.error || 'Erreur inconnue'}`);
                    this.hideProgress();
                }
            } catch (error) {
                console.error('Erreur monitoring:', error);
            }
        }, 2000); // Check toutes les 2 secondes
    }
    
    async getJobStatus() {
        const response = await fetch(`${this.apiBase}/projects/${this.currentProject}/progress`);
        
        if (!response.ok) {
            throw new Error('Impossible de récupérer le statut');
        }
        
        return await response.json();
    }
    
    updateProgress(status) {
        const progressFill = document.getElementById('progress-fill');
        const progressText = document.getElementById('progress-text');
        
        console.log('🔄 UPDATE PROGRESS:', status);
        
        if (status.progress) {
            const { 
                step, total_steps, step_name, progress_percentage, message
            } = status.progress;
            
            // Calcul du pourcentage global
            let percentage = 0;
            if (step && total_steps && progress_percentage !== undefined) {
                // Utiliser le pourcentage du backend
                const stepProgress = ((step - 1) / total_steps) * 100;
                const currentStepProgress = (progress_percentage / total_steps);
                percentage = stepProgress + currentStepProgress;
            } else if (progress_percentage !== undefined) {
                percentage = progress_percentage;
            }
            
            progressFill.style.width = `${Math.min(percentage, 100)}%`;
            
            // Texte de progression
            let displayText = message || step_name || 'Analyse en cours...';
            progressText.textContent = displayText;
            
            // Mettre à jour les étapes visuelles
            if (step && total_steps) {
                for (let i = 1; i <= total_steps; i++) {
                    const stepElement = document.getElementById(`step-${i}`);
                    if (stepElement) {
                        stepElement.classList.remove('active', 'completed');
                        
                        if (i < step) {
                            stepElement.classList.add('completed');
                        } else if (i === step) {
                            stepElement.classList.add('active');
                        }
                    }
                }
            }
        }
    }
    
    showProgress() {
        document.getElementById('progress-section').style.display = 'block';
        document.getElementById('results-section').style.display = 'none';
    }
    
    hideProgress() {
        document.getElementById('progress-section').style.display = 'none';
    }
    
    showResults() {
        this.hideProgress();
        document.getElementById('results-section').style.display = 'block';
        
        // Mettre à jour les statistiques
        this.updateStats();
        
        // Créer la visualisation
        this.createVisualization();
    }
    
    updateStats() {
        const stats = this.results;
        
        document.getElementById('total-pages').textContent = stats.total_pages || 0;
        document.getElementById('total-clusters').textContent = stats.clusters?.length || 0;
        document.getElementById('total-anomalies').textContent = stats.proximities?.length || 0;
        document.getElementById('total-links').textContent = stats.summary?.graph_stats?.total_edges || 0;
    }
    
    createVisualization() {
        const container = document.getElementById('visualization-chart');
        const projection2D = this.results.projection_2d || [];
        
        if (projection2D.length === 0) {
            container.innerHTML = '<p>Aucune donnée de visualisation disponible</p>';
            return;
        }
        
        // Nettoyer le conteneur
        container.innerHTML = '';
        
        // Dimensions
        const margin = {top: 20, right: 20, bottom: 40, left: 40};
        const width = 800 - margin.left - margin.right;
        const height = 500 - margin.top - margin.bottom;
        
        // Créer le SVG
        const svg = d3.select(container)
            .append('svg')
            .attr('width', width + margin.left + margin.right)
            .attr('height', height + margin.top + margin.bottom);
        
        const g = svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Échelles
        const xExtent = d3.extent(projection2D, d => d.x);
        const yExtent = d3.extent(projection2D, d => d.y);
        
        const xScale = d3.scaleLinear()
            .domain(xExtent)
            .range([0, width]);
        
        const yScale = d3.scaleLinear()
            .domain(yExtent)
            .range([height, 0]);
        
        // Couleurs par cluster
        const clusters = [...new Set(projection2D.map(d => d.cluster).filter(c => c !== null))];
        const colorScale = d3.scaleOrdinal(d3.schemeCategory10)
            .domain(clusters);
        
        // Axes
        g.append('g')
            .attr('transform', `translate(0,${height})`)
            .call(d3.axisBottom(xScale))
            .append('text')
            .attr('x', width / 2)
            .attr('y', 35)
            .attr('fill', 'black')
            .style('text-anchor', 'middle')
            .text('Dimension 1');
        
        g.append('g')
            .call(d3.axisLeft(yScale))
            .append('text')
            .attr('transform', 'rotate(-90)')
            .attr('y', -25)
            .attr('x', -height / 2)
            .attr('fill', 'black')
            .style('text-anchor', 'middle')
            .text('Dimension 2');
        
        // Tooltip
        const tooltip = d3.select('body').append('div')
            .attr('class', 'tooltip')
            .style('position', 'absolute')
            .style('padding', '10px')
            .style('background', 'rgba(0,0,0,0.8)')
            .style('color', 'white')
            .style('border-radius', '5px')
            .style('pointer-events', 'none')
            .style('opacity', 0);
        
        // Points
        g.selectAll('.point')
            .data(projection2D)
            .enter()
            .append('circle')
            .attr('class', 'point')
            .attr('cx', d => xScale(d.x))
            .attr('cy', d => yScale(d.y))
            .attr('r', 5)
            .attr('fill', d => d.cluster !== null ? colorScale(d.cluster) : '#999')
            .attr('stroke', '#fff')
            .attr('stroke-width', 1)
            .style('cursor', 'pointer')
            .on('mouseover', function(event, d) {
                tooltip.transition()
                    .duration(200)
                    .style('opacity', .9);
                tooltip.html(`
                    <strong>URL:</strong> ${d.url}<br/>
                    <strong>Cluster:</strong> ${d.cluster !== null ? d.cluster : 'Aucun'}
                `)
                    .style('left', (event.pageX + 10) + 'px')
                    .style('top', (event.pageY - 28) + 'px');
            })
            .on('mouseout', function() {
                tooltip.transition()
                    .duration(500)
                    .style('opacity', 0);
            });
        
        // Légende
        const legend = g.selectAll('.legend')
            .data(clusters)
            .enter().append('g')
            .attr('class', 'legend')
            .attr('transform', (d, i) => `translate(${width - 100}, ${i * 20})`);
        
        legend.append('rect')
            .attr('x', 0)
            .attr('width', 18)
            .attr('height', 18)
            .style('fill', d => colorScale(d));
        
        legend.append('text')
            .attr('x', 24)
            .attr('y', 9)
            .attr('dy', '.35em')
            .style('text-anchor', 'start')
            .style('font-size', '12px')
            .text(d => `Cluster ${d}`);
    }
    
    async loadMockData() {
        try {
            console.log('🎭 Chargement des données mock...');
            
            // Créer un projet factice
            this.currentProject = 'mock-project-id';
            
            // Charger les données mock
            const response = await fetch(`${this.apiBase}/projects/mock-project-id/mock-results`);
            
            if (!response.ok) {
                throw new Error('Impossible de charger les données mock');
            }
            
            this.results = await response.json();
            console.log('🎭 Données mock chargées:', this.results);
            
            // Afficher directement les résultats
            this.showResults();
            
        } catch (error) {
            console.error('Erreur mock:', error);
            this.showError(`Erreur lors du chargement des données mock: ${error.message}`);
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('error-message');
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
    }
    
    showClusters() {
        const container = document.getElementById('visualization-chart');
        const allClusters = this.results.clusters || [];
        
        // Filtrer les clusters par taille minimum (contrôle utilisateur)
        const minSizeFilter = this.clusterMinSizeFilter || 1;
        const clusters = allClusters.filter(cluster => cluster.size >= minSizeFilter);
        
        let html = `
            <div class="clusters-content">
                <div class="clusters-header">
                    <h3>🎯 Clusters Thématiques (${clusters.length}/${allClusters.length})</h3>
                    <div class="cluster-controls">
                        <label>Taille min: 
                            <input type="range" id="cluster-size-slider" 
                                   min="1" max="${Math.max(...allClusters.map(c => c.size))}" 
                                   value="${minSizeFilter}" 
                                   oninput="window.cartographyApp.updateClusterFilter(this.value)">
                            <span id="cluster-size-value">${minSizeFilter}</span>
                        </label>
                        <button class="export-csv-btn" onclick="window.cartographyApp.exportClustersCSV()">
                            📥 Exporter CSV
                        </button>
                    </div>
                </div>
                <div class="clusters-table">
                    <table>
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Thème</th>
                                <th>Nb Pages</th>
                                <th>Toutes les URLs</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        clusters.forEach((cluster, index) => {
            const color = d3.schemeCategory10[index % 10];
            
            html += `
                <tr>
                    <td>
                        <span class="cluster-id" style="background-color: ${color};">
                            ${cluster.cluster_id}
                        </span>
                    </td>
                    <td class="cluster-theme">${cluster.theme}</td>
                    <td class="cluster-size">${cluster.size}</td>
                    <td class="cluster-urls">
                        ${cluster.urls.map(url => `<div><a href="${url}" target="_blank">${url}</a></div>`).join('')}
                    </td>
                </tr>
            `;
        });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
            <style>
                .clusters-content { padding: 20px; }
                .clusters-header { margin-bottom: 20px; }
                .clusters-header h3 { margin: 0; margin-bottom: 10px; }
                .cluster-controls { display: flex; justify-content: space-between; align-items: center; gap: 20px; }
                .cluster-controls label { display: flex; align-items: center; gap: 10px; font-weight: bold; }
                .cluster-controls input[type="range"] { width: 150px; }
                #cluster-size-value { background: #007bff; color: white; padding: 2px 8px; border-radius: 3px; }
                .export-csv-btn { 
                    background: #28a745; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    font-size: 14px;
                }
                .export-csv-btn:hover { background: #218838; }
                .clusters-table { margin-top: 20px; overflow-x: auto; }
                .clusters-table table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .clusters-table th, .clusters-table td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; vertical-align: top; }
                .clusters-table th { background-color: #f8f9fa; font-weight: bold; color: #495057; }
                .clusters-table tr:hover { background-color: #f8f9fa; }
                .cluster-id { color: white; padding: 4px 8px; border-radius: 50%; font-size: 12px; font-weight: bold; display: inline-block; min-width: 20px; text-align: center; }
                .cluster-theme { font-weight: bold; color: #333; }
                .cluster-size { font-weight: bold; color: #666; text-align: center; }
                .cluster-urls div { margin: 2px 0; }
                .cluster-urls a { color: #007bff; text-decoration: none; font-size: 13px; }
                .cluster-urls a:hover { text-decoration: underline; }
            </style>
        `;
        
        container.innerHTML = html;
    }
    
    exportClustersCSV() {
        const clusters = this.results.clusters || [];
        
        // Créer les données CSV
        let csvContent = "Cluster_ID,Theme,Nb_Pages,URL\n";
        
        clusters.forEach(cluster => {
            cluster.urls.forEach(url => {
                csvContent += `${cluster.cluster_id},"${cluster.theme}",${cluster.size},"${url}"\n`;
            });
        });
        
        // Créer et télécharger le fichier
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `clusters_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('✅ CSV clusters exporté avec succès');
    }
    
    showAnomalies() {
        const container = document.getElementById('visualization-chart');
        const proximities = this.results.proximities || [];
        
        let html = `
            <div class="anomalies-content">
                <div class="anomalies-header">
                    <div>
                        <h3>⚠️ Anomalies de Proximité (${proximities.length})</h3>
                        <p>Pages sémantiquement similaires mais éloignées dans la structure de liens</p>
                    </div>
                    <button class="export-csv-btn" onclick="window.cartographyApp.exportAnomaliesCSV()">
                        📥 Exporter CSV
                    </button>
                </div>
                <div class="anomalies-table">
                    <table>
                        <thead>
                            <tr>
                                <th>Score Anomalie</th>
                                <th>Similarité Sémantique</th>
                                <th>Distance Liens</th>
                                <th>Page 1</th>
                                <th>Page 2</th>
                            </tr>
                        </thead>
                        <tbody>
        `;
        
        proximities
            .sort((a, b) => b.anomaly_score - a.anomaly_score)
            .forEach(prox => {
                const scoreColor = prox.anomaly_score > 0.8 ? '#dc3545' : prox.anomaly_score > 0.6 ? '#fd7e14' : '#ffc107';
                html += `
                    <tr>
                        <td>
                            <span class="score-badge" style="background-color: ${scoreColor};">
                                ${Math.round(prox.anomaly_score * 100)}%
                            </span>
                        </td>
                        <td>${Math.round(prox.cosine * 100)}%</td>
                        <td>${prox.hops} liens</td>
                        <td><a href="${prox.url_i}" target="_blank">${prox.url_i}</a></td>
                        <td><a href="${prox.url_j}" target="_blank">${prox.url_j}</a></td>
                    </tr>
                `;
            });
        
        html += `
                        </tbody>
                    </table>
                </div>
            </div>
            <style>
                .anomalies-content { padding: 20px; }
                .anomalies-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
                .anomalies-header div h3 { margin: 0 0 5px 0; }
                .anomalies-header div p { margin: 0; color: #666; font-size: 14px; }
                .export-csv-btn { 
                    background: #28a745; 
                    color: white; 
                    border: none; 
                    padding: 8px 16px; 
                    border-radius: 5px; 
                    cursor: pointer; 
                    font-size: 14px;
                    margin-top: 10px;
                }
                .export-csv-btn:hover { background: #218838; }
                .anomalies-table { margin-top: 20px; overflow-x: auto; }
                .anomalies-table table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
                .anomalies-table th, .anomalies-table td { padding: 12px; text-align: left; border-bottom: 1px solid #dee2e6; }
                .anomalies-table th { background-color: #f8f9fa; font-weight: bold; color: #495057; }
                .anomalies-table tr:hover { background-color: #f8f9fa; }
                .score-badge { color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px; font-weight: bold; }
                .anomalies-table a { color: #007bff; text-decoration: none; }
                .anomalies-table a:hover { text-decoration: underline; }
            </style>
        `;
        
        container.innerHTML = html;
    }
    
    exportAnomaliesCSV() {
        const proximities = this.results.proximities || [];
        
        // Créer les données CSV
        let csvContent = "Score_Anomalie,Similarite_Semantique,Distance_Liens,URL_Page_1,URL_Page_2,Node_ID_1,Node_ID_2\n";
        
        proximities
            .sort((a, b) => b.anomaly_score - a.anomaly_score)
            .forEach(prox => {
                csvContent += `${prox.anomaly_score.toFixed(3)},${prox.cosine.toFixed(3)},${prox.hops},"${prox.url_i}","${prox.url_j}","${prox.node_i}","${prox.node_j}"\n`;
            });
        
        // Créer et télécharger le fichier
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const link = document.createElement('a');
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', `anomalies_${new Date().toISOString().split('T')[0]}.csv`);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        console.log('✅ CSV anomalies exporté avec succès');
    }

    hideError() {
        document.getElementById('error-message').style.display = 'none';
    }

    updateClusterFilter(minSize) {
        this.clusterMinSizeFilter = parseInt(minSize);
        document.getElementById('cluster-size-value').textContent = minSize;
        this.showClusters();
    }

    async loadSavedProjects() {
        try {
            const response = await fetch(`${this.apiBase}/projects/database/projects`);
            const projects = await response.json();
            
            const select = document.getElementById('saved-projects');
            select.innerHTML = '<option value="">Sélectionner un projet...</option>';
            
            projects.forEach(project => {
                const option = document.createElement('option');
                option.value = project.id;
                
                const analysisInfo = project.latest_analysis ? 
                    ` (${project.latest_analysis.total_clusters} clusters, ${project.latest_analysis.created_at.split('T')[0]})` : 
                    ' (pas d\'analyse)';
                    
                option.textContent = `${project.name}${analysisInfo}`;
                select.appendChild(option);
            });
            
        } catch (error) {
            console.error('Erreur lors du chargement des projets:', error);
            const select = document.getElementById('saved-projects');
            select.innerHTML = '<option value="">Erreur de chargement</option>';
        }
    }

    async loadSelectedProject() {
        const projectId = document.getElementById('saved-projects').value;
        if (!projectId) {
            alert('Veuillez sélectionner un projet');
            return;
        }

        try {
            // Récupérer la liste des analyses du projet
            const analysesResponse = await fetch(`${this.apiBase}/projects/${projectId}/analyses`);
            const analyses = await analysesResponse.json();
            
            // Trouver la dernière analyse terminée
            const completedAnalysis = analyses.find(a => a.status === 'completed');
            
            if (!completedAnalysis) {
                alert('Aucune analyse terminée trouvée pour ce projet');
                return;
            }
            
            // Charger les résultats de l'analyse
            const resultsResponse = await fetch(`${this.apiBase}/projects/${projectId}/analyses/${completedAnalysis.id}`);
            const data = await resultsResponse.json();
            
            // Mettre à jour l'interface
            this.currentProjectId = projectId;
            this.results = data.results;
            
            // Afficher les résultats
            this.hideProgress();
            this.showResults();
            
            // Masquer le formulaire d'upload
            document.querySelector('.upload-section').style.display = 'none';
            
            console.log(`Analyse chargée: ${completedAnalysis.total_clusters} clusters, ${completedAnalysis.total_anomalies} anomalies`);
            
        } catch (error) {
            console.error('Erreur lors du chargement de l\'analyse:', error);
            alert('Erreur lors du chargement de l\'analyse');
        }
    }

    debugFileInputs() {
        console.log('🔍 === DIAGNOSTIC FILE INPUTS ===');
        
        // Vérifier que les éléments HTML existent
        const pagesUpload = document.getElementById('pages-upload');
        const linksUpload = document.getElementById('links-upload');
        const pagesFile = document.getElementById('pages-file');
        const linksFile = document.getElementById('links-file');
        
        console.log('📄 Pages upload div:', pagesUpload);
        console.log('🔗 Links upload div:', linksUpload);
        console.log('📄 Pages file input:', pagesFile);
        console.log('🔗 Links file input:', linksFile);
        
        // Test de clic programmatique
        if (pagesFile) {
            console.log('🖱️ Testing pages file click...');
            try {
                pagesFile.click();
                console.log('✅ Pages file click worked');
            } catch (e) {
                console.error('❌ Pages file click failed:', e);
            }
        }
        
        console.log('🔍 === END DIAGNOSTIC ===');
    }
}

// Fonction pour changer d'onglet
function showTab(tabName) {
    // Mettre à jour les onglets actifs
    document.querySelectorAll('.results-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    event.target.classList.add('active');
    
    const app = window.cartographyApp;
    console.log('🔍 DEBUG showTab:', { tabName, app: !!app, results: !!app?.results });
    
    if (!app || !app.results) {
        console.log('❌ No app or results available');
        document.getElementById('visualization-chart').innerHTML = '<p>Aucune donnée disponible</p>';
        return;
    }
    
    console.log('✅ App and results available, switching to tab:', tabName);
    const container = document.getElementById('visualization-chart');
    
    switch(tabName) {
        case 'visualization':
            app.createVisualization();
            break;
        case 'clusters':
            console.log('📊 Calling showClusters with data:', app.results.clusters);
            app.showClusters();
            break;
        case 'anomalies':
            console.log('⚠️ Calling showAnomalies with data:', app.results.proximities);
            app.showAnomalies();
            break;
    }
}

// Initialiser l'application
document.addEventListener('DOMContentLoaded', () => {
    window.cartographyApp = new CartographyApp();
    
    // Charger la liste des projets sauvegardés
    window.cartographyApp.loadSavedProjects();
    
    // Event listener pour le bouton de chargement
    document.getElementById('load-project-btn').addEventListener('click', () => {
        window.cartographyApp.loadSelectedProject();
    });
    
    // Diagnostic après 2 secondes pour s'assurer que tout est chargé
    setTimeout(() => {
        window.cartographyApp.debugFileInputs();
    }, 2000);
});