@extends('layouts.app')

@section('title', 'Alertas - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/alertas.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Alertas del Sistema</h1>
    <div class="header-actions">
        <a href="{{ route('alertas.create') }}" class="btn btn-primary">+ Nueva Alerta</a>
    </div>
</div>

<div class="card">
    <div class="card-body" id="alertas-container">
        <div class="table-empty">
            <div class="table-empty-icon">🔔</div>
            <div class="table-empty-text">Cargando alertas...</div>
        </div>
    </div>
</div>
@endsection

@section('scripts')
<script>
async function loadAlertas() {
    try {
        const alertas = await alertasAPI.getAll();
        const container = document.getElementById('alertas-container');
        
        if (alertas.length === 0) {
            container.innerHTML = `
                <div class="table-empty">
                    <div class="table-empty-icon">🔔</div>
                    <div class="table-empty-text">No hay alertas</div>
                    <div class="table-empty-description">Todo está funcionando correctamente</div>
                </div>
            `;
        } else {
            let html = '<table class="data-table"><thead><tr><th>Empresa</th><th>Tipo</th><th>Mensaje</th><th>Fecha</th><th>Acciones</th></tr></thead><tbody>';
            
            alertas.forEach(alerta => {
                const tipoClass = alerta.tipo_alerta.toLowerCase().includes('error') ? 'alert-error' : 
                                 alerta.tipo_alerta.toLowerCase().includes('warning') ? 'alert-warning' : 'alert-info';
                
                html += `
                    <tr>
                        <td><strong>${alerta.empresa?.nombre || 'N/A'}</strong></td>
                        <td><span class="badge ${tipoClass}">${alerta.tipo_alerta}</span></td>
                        <td>${alerta.mensaje}</td>
                        <td>${formatDate(alerta.fecha)}</td>
                        <td>
                            <div class="table-actions">
                                <button class="table-action-btn danger" onclick="deleteAlerta(${alerta.id})">Eliminar</button>
                            </div>
                        </td>
                    </tr>
                `;
            });
            
            html += '</tbody></table>';
            container.innerHTML = html;
        }
    } catch (error) {
        showError(error);
    }
}

async function deleteAlerta(id) {
    if (confirm('¿Estás seguro de que deseas eliminar esta alerta?')) {
        try {
            await alertasAPI.delete(id);
            showNotification('Alerta eliminada correctamente', 'success');
            loadAlertas();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadAlertas);
</script>
@endsection
