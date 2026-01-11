{% extends "inicio.html" %}

{% block content %}
<div class="dashboard-main-container">
    <h1 class="content-title">
        <i class="fas fa-chart-line"></i> Dashboard Administrativo - Actividades por Aspecto
    </h1>
    
    <!-- Filtros -->
    <div class="filtros-section">
        <div class="filtros-header">
            <h2><i class="fas fa-filter"></i> Filtros de Búsqueda</h2>
            <button class="btn-limpiar" onclick="limpiarFiltros()">
                <i class="fas fa-eraser"></i> Limpiar Filtros
            </button>
        </div>
        
        <div class="filtros-grid">
            <!-- Filtro por Tipo -->
            <div class="filtro-box">
                <h3><i class="fas fa-balance-scale"></i> Tipo de Actividad</h3>
                <div class="tipo-filtro-options">
                    <button class="tipo-filtro-btn all-tipo selected" onclick="seleccionarFiltroTipo('all')">
                        Todos
                    </button>
                    <button class="tipo-filtro-btn positivo" onclick="seleccionarFiltroTipo('Positivo')">
                        <i class="fas fa-thumbs-up"></i> Positivas
                    </button>
                    <button class="tipo-filtro-btn negativo" onclick="seleccionarFiltroTipo('Negativo')">
                        <i class="fas fa-thumbs-down"></i> Negativas
                    </button>
                </div>
            </div>
            
            <!-- Filtro por Bloque CANVA -->
            <div class="filtro-box">
                <h3><i class="fas fa-layer-group"></i> Bloque/Aspecto</h3>
                <select id="filtro-bloque" class="select-filtro" onchange="aplicarFiltros()">
                    <option value="all">Todos los bloques</option>
                    {% for bloque in bloques_canva %}
                    <option value="{{ bloque.nombre }}">{{ loop.index }}. {{ bloque.nombre }}</option>
                    {% endfor %}
                    <!-- Opciones para FODA -->
                    <option value="POLITICO">POLITICO</option>
                    <option value="ECONOMICO">ECONOMICO</option>
                    <option value="SOCIAL">SOCIAL</option>
                    <option value="TECNOLOGICO">TECNOLOGICO</option>
                    <option value="ECOLOGICO">ECOLOGICO</option>
                    <option value="LEGAL">LEGAL</option>
                </select>
            </div>
            
            <!-- Filtro por Fuente -->
            <div class="filtro-box">
                <h3><i class="fas fa-database"></i> Fuente</h3>
                <select id="filtro-fuente" class="select-filtro" onchange="aplicarFiltros()">
                    <option value="all">Todas las fuentes</option>
                    <option value="canva">CANVA</option>
                    <option value="foda_ext">FODA Externo</option>
                    <option value="foda_int">FODA Interno</option>
                    <option value="manual">Manual</option>
                    <option value="importado">Importado</option>
                </select>
            </div>
            
            <!-- Filtro por Fecha -->
            <div class="filtro-box">
                <h3><i class="fas fa-calendar-alt"></i> Rango de Fechas</h3>
                <div class="fecha-filtro">
                    <div class="fecha-input">
                        <label for="fecha-desde">Desde:</label>
                        <input type="date" id="fecha-desde" class="date-input" onchange="aplicarFiltros()">
                    </div>
                    <div class="fecha-input">
                        <label for="fecha-hasta">Hasta:</label>
                        <input type="date" id="fecha-hasta" class="date-input" onchange="aplicarFiltros()">
                    </div>
                </div>
            </div>
            
            <!-- Filtro por Palabra Clave -->
            <div class="filtro-box">
                <h3><i class="fas fa-search"></i> Palabra Clave</h3>
                <div class="search-box">
                    <input type="text" id="filtro-busqueda" class="search-input" 
                           placeholder="Buscar en actividades..." onkeyup="aplicarFiltros()">
                    <i class="fas fa-search search-icon"></i>
                </div>
            </div>
            
            <!-- Ordenamiento -->
            <div class="filtro-box">
                <h3><i class="fas fa-sort"></i> Ordenar por</h3>
                <select id="ordenar-por" class="select-filtro" onchange="aplicarFiltros()">
                    <option value="fecha_desc">Fecha (más reciente primero)</option>
                    <option value="fecha_asc">Fecha (más antiguo primero)</option>
                    <option value="actividad_asc">Actividad (A-Z)</option>
                    <option value="actividad_desc">Actividad (Z-A)</option>
                    <option value="tipo_asc">Tipo (A-Z)</option>
                </select>
            </div>
        </div>
        
        <div class="filtros-actions">
            <button class="btn-aplicar" onclick="aplicarFiltros()">
                <i class="fas fa-check-circle"></i> Aplicar Filtros
            </button>
            <button class="btn-exportar" onclick="exportarDatos()">
                <i class="fas fa-file-export"></i> Exportar Datos
            </button>
        </div>
    </div>
    
    <!-- Resumen Estadístico -->
    <div class="estadisticas-section">
        <h2><i class="fas fa-chart-pie"></i> Resumen Estadístico</h2>
        <div class="estadisticas-grid">
            <div class="estadistica-card total">
                <div class="estadistica-icon">
                    <i class="fas fa-list-alt"></i>
                </div>
                <div class="estadistica-content">
                    <h3>Total Actividades</h3>
                    <div class="estadistica-valor" id="total-actividades">{{ total_actividades }}</div>
                </div>
            </div>
            
            <div class="estadistica-card positivas">
                <div class="estadistica-icon">
                    <i class="fas fa-thumbs-up"></i>
                </div>
                <div class="estadistica-content">
                    <h3>Actividades Positivas</h3>
                    <div class="estadistica-valor" id="total-positivas">{{ actividades_positivas }}</div>
                </div>
            </div>
            
            <div class="estadistica-card negativas">
                <div class="estadistica-icon">
                    <i class="fas fa-thumbs-down"></i>
                </div>
                <div class="estadistica-content">
                    <h3>Actividades Negativas</h3>
                    <div class="estadistica-valor" id="total-negativas">{{ actividades_negativas }}</div>
                </div>
            </div>
            
            <div class="estadistica-card usuarios">
                <div class="estadistica-icon">
                    <i class="fas fa-users"></i>
                </div>
                <div class="estadistica-content">
                    <h3>Usuarios</h3>
                    <div class="estadistica-valor" id="total-usuarios">{{ usuarios_count }}</div>
                </div>
            </div>
            
            <div class="estadistica-card canva">
                <div class="estadistica-icon">
                    <i class="fas fa-th-large"></i>
                </div>
                <div class="estadistica-content">
                    <h3>CANVA</h3>
                    <div class="estadistica-valor" id="total-canva">{{ total_actividades_canva }}</div>
                </div>
            </div>
            
            <div class="estadistica-card foda-ext">
                <div class="estadistica-icon">
                    <i class="fas fa-external-link-alt"></i>
                </div>
                <div class="estadistica-content">
                    <h3>FODA Externo</h3>
                    <div class="estadistica-valor" id="total-foda-ext">{{ total_actividades_foda_ext }}</div>
                </div>
            </div>
            
            <div class="estadistica-card foda-int">
                <div class="estadistica-icon">
                    <i class="fas fa-internal-link"></i>
                </div>
                <div class="estadistica-content">
                    <h3>FODA Interno</h3>
                    <div class="estadistica-valor" id="total-foda-int">{{ total_actividades_foda_int }}</div>
                </div>
            </div>
            
            <div class="estadistica-card recientes">
                <div class="estadistica-icon">
                    <i class="fas fa-clock"></i>
                </div>
                <div class="estadistica-content">
                    <h3>Últimas 24h</h3>
                    <div class="estadistica-valor" id="total-recientes">0</div>
                </div>
            </div>
        </div>
    </div>
    
    <!-- Tabla de Actividades -->
    <div class="tabla-section">
        <div class="tabla-header">
            <h2><i class="fas fa-table"></i> Lista de Actividades</h2>
            <div class="tabla-info">
                <span id="registros-mostrados">Mostrando 0 de 0 registros</span>
                <div class="paginacion-control">
                    <button class="paginacion-btn" onclick="cambiarPagina(-1)">
                        <i class="fas fa-chevron-left"></i> Anterior
                    </button>
                    <span class="pagina-actual" id="pagina-actual">Página 1</span>
                    <button class="paginacion-btn" onclick="cambiarPagina(1)">
                        Siguiente <i class="fas fa-chevron-right"></i>
                    </button>
                </div>
            </div>
        </div>
        
        <div class="table-container">
            <table class="dashboard-table" id="tabla-actividades">
                <thead>
                    <tr>
                        <th width="5%">ID</th>
                        <th width="25%">Actividad</th>
                        <th width="10%">Tipo</th>
                        <th width="15%">Bloque/Aspecto</th>
                        <th width="15%">Descripción</th>
                        <th width="10%">Fuente</th>
                        <th width="15%">Fecha</th>
                        <th width="5%">Acciones</th>
                    </tr>
                </thead>
                <tbody id="tabla-body">
                    <!-- Los datos se cargarán dinámicamente -->
                </tbody>
            </table>
        </div>
        
        <div class="tabla-footer">
            <div class="resultados-por-pagina">
                <label for="resultados-pagina">Resultados por página:</label>
                <select id="resultados-pagina" class="select-paginacion" onchange="cambiarResultadosPorPagina()">
                    <option value="10">10</option>
                    <option value="25" selected>25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
            
            <button class="btn-refrescar" onclick="cargarDatos()">
                <i class="fas fa-sync-alt"></i> Refrescar Datos
            </button>
        </div>
    </div>
    
    <!-- Gráficos de Distribución -->
    <div class="graficos-section">
        <h2><i class="fas fa-chart-bar"></i> Distribución de Actividades</h2>
        <div class="graficos-grid">
            <div class="grafico-card">
                <h3><i class="fas fa-chart-pie"></i> Por Fuente</h3>
                <div class="grafico-container">
                    <canvas id="grafico-fuente"></canvas>
                </div>
            </div>
            
            <div class="grafico-card">
                <h3><i class="fas fa-chart-bar"></i> Por Tipo</h3>
                <div class="grafico-container">
                    <canvas id="grafico-tipo"></canvas>
                </div>
            </div>
            
            <div class="grafico-card">
                <h3><i class="fas fa-chart-line"></i> Por Día (Últimos 7 días)</h3>
                <div class="grafico-container">
                    <canvas id="grafico-fecha"></canvas>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
    /* Estilos del dashboard (los mismos que antes) */
    .dashboard-main-container {
        padding: 20px;
        background: #f5f7fa;
        min-height: 100vh;
    }
    
    .content-title {
        color: #0c2461;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 3px solid #4a69bd;
        font-size: 28px;
        display: flex;
        align-items: center;
        gap: 15px;
    }
    
    /* ... (mantén todos los estilos CSS del dashboard que proporcioné anteriormente) ... */
    
    /* Añadir estilos para badges de fuente */
    .badge-fuente {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .badge-fuente.canva {
        background-color: #0c2461;
        color: white;
    }
    
    .badge-fuente.foda_ext {
        background-color: #4CAF50;
        color: white;
    }
    
    .badge-fuente.foda_int {
        background-color: #2196F3;
        color: white;
    }
    
    .badge-fuente.manual {
        background-color: #FF9800;
        color: white;
    }
    
    .badge-fuente.importado {
        background-color: #9C27B0;
        color: white;
    }
    
    /* Estilos para botones de acción */
    .acciones-celda {
        display: flex;
        gap: 5px;
    }
    
    .btn-accion {
        width: 30px;
        height: 30px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        transition: all 0.3s;
    }
    
    .btn-accion:hover {
        transform: scale(1.1);
    }
    
    .btn-editar {
        background-color: #4a69bd;
        color: white;
    }
    
    .btn-eliminar {
        background-color: #ff6b6b;
        color: white;
    }
</style>

<script>
    // Variables globales
    let actividadesData = [];
    let actividadesFiltradas = [];
    let paginaActual = 1;
    let resultadosPorPagina = 25;
    let filtroTipo = 'all';
    let filtroBloque = 'all';
    let filtroFuente = 'all';
    let filtroFechaDesde = '';
    let filtroFechaHasta = '';
    let filtroBusqueda = '';
    let ordenarPor = 'fecha_desc';
    
    // Cargar datos al iniciar
    document.addEventListener('DOMContentLoaded', function() {
        cargarDatos();
        actualizarEstadisticas();
        establecerFechasPorDefecto();
        inicializarGraficos();
    });
    
    // Establecer fechas por defecto (últimos 30 días)
    function establecerFechasPorDefecto() {
        const hoy = new Date();
        const hace30Dias = new Date();
        hace30Dias.setDate(hoy.getDate() - 30);
        
        document.getElementById('fecha-desde').value = hace30Dias.toISOString().split('T')[0];
        document.getElementById('fecha-hasta').value = hoy.toISOString().split('T')[0];
        
        filtroFechaDesde = document.getElementById('fecha-desde').value;
        filtroFechaHasta = document.getElementById('fecha-hasta').value;
    }
    
    // Cargar datos desde la API
    function cargarDatos() {
        const tablaBody = document.getElementById('tabla-body');
        tablaBody.innerHTML = `
            <tr>
                <td colspan="8" style="text-align: center; padding: 40px;">
                    <div class="loading"></div>
                    <p>Cargando datos desde la base de datos...</p>
                </td>
            </tr>
        `;
        
        // Obtener valores de filtros
        filtroTipo = obtenerFiltroTipoSeleccionado();
        filtroBloque = document.getElementById('filtro-bloque').value;
        filtroFuente = document.getElementById('filtro-fuente').value;
        filtroFechaDesde = document.getElementById('fecha-desde').value;
        filtroFechaHasta = document.getElementById('fecha-hasta').value;
        filtroBusqueda = document.getElementById('filtro-busqueda').value;
        ordenarPor = document.getElementById('ordenar-por').value;
        
        // Preparar datos para la petición
        const datosFiltro = {
            tipo_filtro: filtroTipo,
            bloque_filtro: filtroBloque,
            fuente_filtro: filtroFuente,
            fecha_desde: filtroFechaDesde,
            fecha_hasta: filtroFechaHasta,
            busqueda: filtroBusqueda,
            orden_por: ordenarPor,
            pagina: paginaActual,
            por_pagina: resultadosPorPagina
        };
        
        // Hacer petición a la API
        fetch('/api/admin/filtrar_actividades', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(datosFiltro)
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                actividadesData = data.actividades;
                actividadesFiltradas = actividadesData;
                actualizarTabla(data);
                actualizarGraficos();
            } else {
                mostrarAlerta('❌ Error al cargar datos: ' + data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarAlerta('❌ Error de conexión al servidor.', 'error');
        });
    }
    
    // Actualizar estadísticas desde la API
    function actualizarEstadisticas() {
        fetch('/api/admin/estadisticas')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    const stats = data.estadisticas;
                    
                    // Actualizar tarjetas de estadísticas
                    document.getElementById('total-actividades').textContent = stats.total_actividades;
                    document.getElementById('total-canva').textContent = stats.actividades_canva;
                    document.getElementById('total-foda-ext').textContent = stats.actividades_foda_ext;
                    document.getElementById('total-foda-int').textContent = stats.actividades_foda_int;
                    document.getElementById('total-positivas').textContent = stats.positivas_canva + stats.positivas_foda_ext;
                    document.getElementById('total-negativas').textContent = stats.negativas_canva + stats.negativas_foda_ext;
                    document.getElementById('total-recientes').textContent = stats.actividades_recientes_7dias;
                    document.getElementById('total-usuarios').textContent = stats.usuarios_total;
                    
                    // Actualizar gráfico de bloques
                    actualizarGraficoBloques(data.bloques_estadisticas);
                }
            })
            .catch(error => {
                console.error('Error al cargar estadísticas:', error);
            });
    }
    
    // Obtener el filtro de tipo seleccionado
    function obtenerFiltroTipoSeleccionado() {
        const botones = document.querySelectorAll('.tipo-filtro-btn.selected');
        for (let boton of botones) {
            if (boton.classList.contains('all-tipo')) return 'all';
            if (boton.classList.contains('positivo')) return 'Positivo';
            if (boton.classList.contains('negativo')) return 'Negativo';
        }
        return 'all';
    }
    
    // Seleccionar filtro de tipo
    function seleccionarFiltroTipo(tipo) {
        // Remover selección de todos los botones
        document.querySelectorAll('.tipo-filtro-btn').forEach(btn => {
            btn.classList.remove('selected');
        });
        
        // Seleccionar el botón correspondiente
        if (tipo === 'all') {
            document.querySelector('.tipo-filtro-btn.all-tipo').classList.add('selected');
        } else if (tipo === 'Positivo') {
            document.querySelector('.tipo-filtro-btn.positivo').classList.add('selected');
        } else if (tipo === 'Negativo') {
            document.querySelector('.tipo-filtro-btn.negativo').classList.add('selected');
        }
        
        aplicarFiltros();
    }
    
    // Aplicar filtros y actualizar tabla
    function aplicarFiltros() {
        paginaActual = 1;
        cargarDatos();
    }
    
    // Actualizar tabla con datos
    function actualizarTabla(data) {
        const tablaBody = document.getElementById('tabla-body');
        const actividades = data.actividades;
        const total = data.total;
        const totalPaginas = data.total_paginas;
        
        if (actividades.length === 0) {
            tablaBody.innerHTML = `
                <tr>
                    <td colspan="8" style="text-align: center; padding: 40px; color: #666;">
                        <i class="fas fa-inbox" style="font-size: 48px; margin-bottom: 15px; color: #dee2e6;"></i>
                        <p>No se encontraron actividades con los filtros aplicados.</p>
                        <button class="btn-limpiar" onclick="limpiarFiltros()" style="margin-top: 15px;">
                            <i class="fas fa-eraser"></i> Limpiar Filtros
                        </button>
                    </td>
                </tr>
            `;
        } else {
            // Generar HTML para las filas
            let html = '';
            actividades.forEach(actividad => {
                const colorTipo = actividad.tipo === 'Positivo' ? '#4CAF50' : '#ff6b6b';
                
                html += `
                    <tr>
                        <td>${actividad.id}</td>
                        <td>${actividad.actividad}</td>
                        <td style="color: ${colorTipo}; font-weight: 600;">${actividad.tipo}</td>
                        <td>${actividad.bloque}</td>
                        <td>${actividad.aspecto}</td>
                        <td>
                            <span class="badge-fuente ${actividad.fuente}">
                                ${actividad.fuente}
                            </span>
                        </td>
                        <td>${formatearFecha(actividad.fecha)}</td>
                        <td class="acciones-celda">
                            <button class="btn-accion btn-editar" onclick="editarActividad(${actividad.id})" title="Editar">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button class="btn-accion btn-eliminar" onclick="eliminarActividad(${actividad.id})" title="Eliminar">
                                <i class="fas fa-trash"></i>
                            </button>
                        </td>
                    </tr>
                `;
            });
            
            tablaBody.innerHTML = html;
        }
        
        // Actualizar información de paginación
        const inicio = ((paginaActual - 1) * resultadosPorPagina) + 1;
        const fin = Math.min(paginaActual * resultadosPorPagina, total);
        
        document.getElementById('registros-mostrados').textContent = 
            `Mostrando ${inicio}-${fin} de ${total} registros`;
        document.getElementById('pagina-actual').textContent = `Página ${paginaActual} de ${totalPaginas}`;
    }
    
    // Formatear fecha para mostrar
    function formatearFecha(fechaStr) {
        if (!fechaStr) return '';
        const fecha = new Date(fechaStr);
        return fecha.toLocaleDateString('es-ES', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    // Cambiar página
    function cambiarPagina(direccion) {
        const totalPaginas = Math.ceil(actividadesFiltradas.length / resultadosPorPagina);
        
        if (direccion === -1 && paginaActual > 1) {
            paginaActual--;
        } else if (direccion === 1 && paginaActual < totalPaginas) {
            paginaActual++;
        }
        
        cargarDatos();
    }
    
    // Cambiar resultados por página
    function cambiarResultadosPorPagina() {
        resultadosPorPagina = parseInt(document.getElementById('resultados-pagina').value);
        paginaActual = 1;
        cargarDatos();
    }
    
    // Limpiar todos los filtros
    function limpiarFiltros() {
        // Restablecer filtros
        seleccionarFiltroTipo('all');
        document.getElementById('filtro-bloque').value = 'all';
        document.getElementById('filtro-fuente').value = 'all';
        document.getElementById('filtro-busqueda').value = '';
        document.getElementById('ordenar-por').value = 'fecha_desc';
        
        // Restablecer fechas a los últimos 30 días
        establecerFechasPorDefecto();
        
        // Aplicar filtros limpios
        aplicarFiltros();
        
        mostrarAlerta('✅ Filtros limpiados correctamente.', 'success');
    }
    
    // Inicializar gráficos
    function inicializarGraficos() {
        // Configuración común para gráficos
        Chart.defaults.font.family = "'Segoe UI', 'Helvetica Neue', Arial, sans-serif";
        Chart.defaults.font.size = 12;
        Chart.defaults.color = '#666';
        
        // Gráfico de fuente
        const ctxFuente = document.getElementById('grafico-fuente').getContext('2d');
        window.graficoFuente = new Chart(ctxFuente, {
            type: 'doughnut',
            data: {
                labels: ['CANVA', 'FODA Externo', 'FODA Interno', 'Manual', 'Importado'],
                datasets: [{
                    data: [0, 0, 0, 0, 0],
                    backgroundColor: ['#0c2461', '#4CAF50', '#2196F3', '#FF9800', '#9C27B0'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 20,
                            usePointStyle: true
                        }
                    }
                }
            }
        });
        
        // Gráfico de tipo
        const ctxTipo = document.getElementById('grafico-tipo').getContext('2d');
        window.graficoTipo = new Chart(ctxTipo, {
            type: 'pie',
            data: {
                labels: ['Positivas', 'Negativas'],
                datasets: [{
                    data: [0, 0],
                    backgroundColor: ['#4CAF50', '#ff6b6b'],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
        
        // Gráfico de fecha
        const ctxFecha = document.getElementById('grafico-fecha').getContext('2d');
        window.graficoFecha = new Chart(ctxFecha, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Actividades por día',
                    data: [],
                    borderColor: '#4a69bd',
                    backgroundColor: 'rgba(74, 105, 189, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }
    
    // Actualizar gráfico de bloques
    function actualizarGraficoBloques(bloquesData) {
        // Si hay un gráfico de barras para bloques, actualízalo aquí
        // Por ahora, solo actualizamos las estadísticas generales
    }
    
    // Actualizar gráficos con datos filtrados
    function actualizarGraficos() {
        if (!window.graficoFuente) return;
        
        // Calcular distribución por fuente
        const fuentes = ['canva', 'foda_ext', 'foda_int', 'manual', 'importado'];
        const datosFuentes = fuentes.map(fuente => 
            actividadesFiltradas.filter(a => a.fuente === fuente).length
        );
        
        window.graficoFuente.data.datasets[0].data = datosFuentes;
        window.graficoFuente.update();
        
        // Calcular distribución por tipo
        const positivas = actividadesFiltradas.filter(a => a.tipo === 'Positivo').length;
        const negativas = actividadesFiltradas.filter(a => a.tipo === 'Negativo').length;
        
        window.graficoTipo.data.datasets[0].data = [positivas, negativas];
        window.graficoTipo.update();
        
        // Calcular distribución por fecha (últimos 7 días)
        const ultimos7Dias = [];
        const hoy = new Date();
        
        for (let i = 6; i >= 0; i--) {
            const fecha = new Date();
            fecha.setDate(hoy.getDate() - i);
            const fechaStr = fecha.toISOString().split('T')[0];
            ultimos7Dias.push(fechaStr);
        }
        
        const actividadesPorFecha = {};
        ultimos7Dias.forEach(fecha => {
            actividadesPorFecha[fecha] = 0;
        });
        
        actividadesFiltradas.forEach(actividad => {
            if (actividad.fecha) {
                const fechaActividad = actividad.fecha.split(' ')[0];
                if (actividadesPorFecha.hasOwnProperty(fechaActividad)) {
                    actividadesPorFecha[fechaActividad]++;
                }
            }
        });
        
        window.graficoFecha.data.labels = ultimos7Dias.map(fecha => {
            const d = new Date(fecha);
            return d.toLocaleDateString('es-ES', { day: '2-digit', month: 'short' });
        });
        window.graficoFecha.data.datasets[0].data = ultimos7Dias.map(fecha => actividadesPorFecha[fecha]);
        window.graficoFecha.update();
    }
    
    // Exportar datos a CSV
    function exportarDatos() {
        mostrarAlerta('📊 Preparando exportación de datos...', 'success');
        
        // Preparar datos para la petición
        const datosFiltro = {
            tipo_filtro: filtroTipo,
            bloque_filtro: filtroBloque,
            fuente_filtro: filtroFuente,
            fecha_desde: filtroFechaDesde,
            fecha_hasta: filtroFechaHasta,
            busqueda: filtroBusqueda,
            orden_por: ordenarPor
        };
        
        // Hacer petición a la API de exportación
        fetch('/api/admin/exportar_datos', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify(datosFiltro)
        })
        .then(response => {
            if (response.ok) {
                return response.blob();
            }
            throw new Error('Error en la exportación');
        })
        .then(blob => {
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `actividades_exportadas_${new Date().toISOString().split('T')[0]}.csv`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            mostrarAlerta('✅ Datos exportados correctamente.', 'success');
        })
        .catch(error => {
            console.error('Error:', error);
            mostrarAlerta('❌ Error al exportar datos.', 'error');
        });
    }
    
    // Editar actividad
    function editarActividad(id) {
        mostrarAlerta('✏️ Función de edición en desarrollo...', 'info');
        // Aquí podrías abrir un modal o redirigir a la página de edición
    }
    
    // Eliminar actividad
    function eliminarActividad(id) {
        if (confirm('⚠️ ¿Está seguro de que desea eliminar esta actividad?\n\nEsta acción no se puede deshacer.')) {
            fetch(`/aspectos/${id}/eliminar`, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mostrarAlerta('✅ Actividad eliminada correctamente.', 'success');
                    cargarDatos(); // Recargar datos
                    actualizarEstadisticas(); // Actualizar estadísticas
                } else {
                    mostrarAlerta('❌ Error: ' + data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                mostrarAlerta('❌ Error de conexión al servidor.', 'error');
            });
        }
    }
    
    // Función para mostrar alertas
    function mostrarAlerta(mensaje, tipo) {
        let alerta = document.getElementById('alerta-flotante');
        
        if (!alerta) {
            alerta = document.createElement('div');
            alerta.id = 'alerta-flotante';
            alerta.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 20px;
                border-radius: 8px;
                color: white;
                font-weight: 600;
                z-index: 10000;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: all 0.3s ease;
                transform: translateX(100%);
                opacity: 0;
                max-width: 400px;
            `;
            document.body.appendChild(alerta);
        }
        
        if (tipo === 'success') {
            alerta.style.backgroundColor = '#4CAF50';
        } else if (tipo === 'error') {
            alerta.style.backgroundColor = '#ff6b6b';
        } else if (tipo === 'info') {
            alerta.style.backgroundColor = '#2196F3';
        } else {
            alerta.style.backgroundColor = '#FF9800';
        }
        
        alerta.innerHTML = `<i class="fas fa-${tipo === 'success' ? 'check-circle' : tipo === 'error' ? 'exclamation-circle' : 'info-circle'}"></i> ${mensaje}`;
        
        setTimeout(() => {
            alerta.style.transform = 'translateX(0)';
            alerta.style.opacity = '1';
        }, 10);
        
        setTimeout(() => {
            alerta.style.transform = 'translateX(100%)';
            alerta.style.opacity = '0';
        }, 4000);
    }
</script>
{% endblock %}
