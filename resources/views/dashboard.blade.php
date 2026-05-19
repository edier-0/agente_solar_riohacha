@extends('layouts.app')

@section('title', 'Dashboard - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/dashboard.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Dashboard</h1>
    <div class="header-actions">
        <button class="btn btn-primary" onclick="loadDashboardData()">Actualizar</button>
    </div>
</div>

<!-- KPIs -->
<div class="grid grid-4 mb-lg">
    <div class="kpi-card">
        <div class="kpi-icon blue">☀️</div>
        <div class="kpi-label">Radiación Actual</div>
        <div class="kpi-value" id="radiacion-actual">--</div>
        <div class="kpi-unit">W/m²</div>
        <div class="kpi-trend up">↑ 5.2%</div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-icon green">💰</div>
        <div class="kpi-label">Costo Proyectado</div>
        <div class="kpi-value" id="costo-proyectado">--</div>
        <div class="kpi-unit">COP/mes</div>
        <div class="kpi-trend down">↓ 3.1%</div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-icon green">🌱</div>
        <div class="kpi-label">Ahorro Solar</div>
        <div class="kpi-value" id="ahorro-solar">--</div>
        <div class="kpi-unit">COP/mes</div>
        <div class="kpi-trend up">↑ 12.5%</div>
    </div>
    
    <div class="kpi-card">
        <div class="kpi-icon yellow">⚠️</div>
        <div class="kpi-label">Estado de Red</div>
        <div class="kpi-value" id="estado-red">Normal</div>
        <div class="kpi-unit">Estable</div>
    </div>
</div>

<!-- Alertas Recientes -->
<div class="card mb-lg">
    <div class="card-header">
        <h3>Alertas Recientes</h3>
        <a href="{{ route('alertas.index') }}" class="btn btn-secondary btn-small">Ver todas</a>
    </div>
    <div class="card-body" id="alertas-container">
        <div class="table-empty">
            <div class="table-empty-icon">🔔</div>
            <div class="table-empty-text">No hay alertas</div>
            <div class="table-empty-description">Todo está funcionando correctamente</div>
        </div>
    </div>
</div>

<!-- Empresas Registradas -->
<div class="card">
    <div class="card-header">
        <h3>Empresas Registradas</h3>
        <a href="{{ route('empresas.create') }}" class="btn btn-primary btn-small">+ Nueva Empresa</a>
    </div>
    <div class="card-body">
        <table class="data-table" id="empresas-table">
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Consumo Diario</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="empresas-tbody">
                <tr>
                    <td colspan="4" class="text-center text-muted">Cargando...</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
@endsection

@section('scripts')
<script>
async function loadDashboardData() {
    try {
        // Cargar radiación solar
        const radiaciones = await radiacionesAPI.getAll();
        if (radiaciones.length > 0) {
            const latest = radiaciones[radiaciones.length - 1];
            document.getElementById('radiacion-actual').textContent = 
                (latest.radiacion_actual || 0).toFixed(2);
        }
        
        // Cargar empresas
        const empresas = await empresasAPI.getAll();
        const tbody = document.getElementById('empresas-tbody');
        
        if (empresas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center text-muted">No hay empresas registradas</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = empresas.map(empresa => `
                <tr>
                    <td>${empresa.nombre}</td>
                    <td><span class="badge badge-info">${empresa.tipo}</span></td>
                    <td>-- kWh</td>
                    <td>
                        <div class="table-actions">
                            <a href="/empresas/${empresa.id}" class="table-action-btn">Ver</a>
                            <a href="/empresas/${empresa.id}/edit" class="table-action-btn">Editar</a>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
        
        // Cargar alertas
        const alertas = await alertasAPI.getAll();
        const alertasContainer = document.getElementById('alertas-container');
        
        if (alertas.length === 0) {
            alertasContainer.innerHTML = `
                <div class="table-empty">
                    <div class="table-empty-icon">🔔</div>
                    <div class="table-empty-text">No hay alertas</div>
                    <div class="table-empty-description">Todo está funcionando correctamente</div>
                </div>
            `;
        } else {
            alertasContainer.innerHTML = alertas.slice(-5).map(alerta => `
                <div class="alert alert-warning">
                    <div class="alert-icon">⚠️</div>
                    <div class="alert-content">
                        <div class="alert-title">${alerta.tipo_alerta}</div>
                        <div class="alert-message">${alerta.mensaje}</div>
                    </div>
                </div>
            `).join('');
        }
        
    } catch (error) {
        showError(error);
    }
}

// Cargar datos al iniciar
document.addEventListener('DOMContentLoaded', loadDashboardData);
</script>
@endsection
