@extends('layouts.app')

@section('title', 'Radiación Solar - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/radiaciones.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Radiación Solar</h1>
    <div class="header-actions">
        <a href="{{ route('radiaciones.create') }}" class="btn btn-primary">+ Nuevo Registro</a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <table class="data-table" id="radiaciones-table">
            <thead>
                <tr>
                    <th>Fecha</th>
                    <th>Radiación Histórica (W/m²)</th>
                    <th>Radiación Actual (W/m²)</th>
                    <th>Temperatura (°C)</th>
                    <th>Nubosidad (%)</th>
                    <th>Clima</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="radiaciones-tbody">
                <tr>
                    <td colspan="7" class="text-center text-muted">Cargando...</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
@endsection

@section('scripts')
<script>
async function loadRadiaciones() {
    try {
        const radiaciones = await radiacionesAPI.getAll();
        const tbody = document.getElementById('radiaciones-tbody');
        
        if (radiaciones.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-center text-muted">No hay registros de radiación</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = radiaciones.map(radiacion => `
                <tr>
                    <td>${formatDate(radiacion.fecha)}</td>
                    <td>${(radiacion.radiacion_historica || 0).toFixed(2)}</td>
                    <td>${(radiacion.radiacion_actual || 0).toFixed(2)}</td>
                    <td>${(radiacion.temperatura || 0).toFixed(2)}</td>
                    <td>${(radiacion.nubosidad || 0).toFixed(2)}</td>
                    <td>${radiacion.clima || 'N/A'}</td>
                    <td>
                        <div class="table-actions">
                            <a href="/radiaciones/${radiacion.id}/edit" class="table-action-btn">Editar</a>
                            <button class="table-action-btn danger" onclick="deleteRadiacion(${radiacion.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showError(error);
    }
}

async function deleteRadiacion(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este registro?')) {
        try {
            await radiacionesAPI.delete(id);
            showNotification('Registro eliminado correctamente', 'success');
            loadRadiaciones();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadRadiaciones);
</script>
@endsection
