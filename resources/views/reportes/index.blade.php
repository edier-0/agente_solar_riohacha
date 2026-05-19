@extends('layouts.app')

@section('title', 'Reportes - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/reportes.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Reportes</h1>
    <div class="header-actions">
        <a href="{{ route('reportes.create') }}" class="btn btn-primary">+ Nuevo Reporte</a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <table class="data-table" id="reportes-table">
            <thead>
                <tr>
                    <th>Empresa</th>
                    <th>Fecha</th>
                    <th>Tipo</th>
                    <th>Nombre del Archivo</th>
                    <th>Creado</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="reportes-tbody">
                <tr>
                    <td colspan="6" class="text-center text-muted">Cargando...</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
@endsection

@section('scripts')
<script>
async function loadReportes() {
    try {
        const reportes = await reportesAPI.getAll();
        const tbody = document.getElementById('reportes-tbody');
        
        if (reportes.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">No hay reportes</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = reportes.map(reporte => `
                <tr>
                    <td><strong>${reporte.empresa?.nombre || 'N/A'}</strong></td>
                    <td>${formatDate(reporte.fecha)}</td>
                    <td><span class="badge badge-info">${reporte.tipo}</span></td>
                    <td>${reporte.nombre_archivo || 'N/A'}</td>
                    <td>${formatDate(reporte.created_at)}</td>
                    <td>
                        <div class="table-actions">
                            <a href="/reportes/${reporte.id}/edit" class="table-action-btn">Editar</a>
                            <button class="table-action-btn danger" onclick="deleteReporte(${reporte.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showError(error);
    }
}

async function deleteReporte(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este reporte?')) {
        try {
            await reportesAPI.delete(id);
            showNotification('Reporte eliminado correctamente', 'success');
            loadReportes();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadReportes);
</script>
@endsection
