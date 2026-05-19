@extends('layouts.app')

@section('title', 'Consumos Energéticos - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/consumos.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Consumos Energéticos</h1>
    <div class="header-actions">
        <a href="{{ route('consumos.create') }}" class="btn btn-primary">+ Nuevo Consumo</a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <table class="data-table" id="consumos-table">
            <thead>
                <tr>
                    <th>Empresa</th>
                    <th>Fecha</th>
                    <th>Consumo Diario (kWh)</th>
                    <th>Tarifa (COP/kWh)</th>
                    <th>Costo Estimado</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="consumos-tbody">
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
async function loadConsumos() {
    try {
        const consumos = await consumosAPI.getAll();
        const tbody = document.getElementById('consumos-tbody');
        
        if (consumos.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="text-center text-muted">No hay registros de consumo</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = consumos.map(consumo => {
                const costo = (consumo.consumo_diario || 0) * (consumo.tarifa || 0);
                return `
                    <tr>
                        <td><strong>${consumo.empresa?.nombre || 'N/A'}</strong></td>
                        <td>${formatDate(consumo.fecha)}</td>
                        <td>${(consumo.consumo_diario || 0).toFixed(2)}</td>
                        <td>${(consumo.tarifa || 0).toFixed(2)}</td>
                        <td>${formatCurrency(costo)}</td>
                        <td>
                            <div class="table-actions">
                                <a href="/consumos/${consumo.id}/edit" class="table-action-btn">Editar</a>
                                <button class="table-action-btn danger" onclick="deleteConsumo(${consumo.id})">Eliminar</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
        }
    } catch (error) {
        showError(error);
    }
}

async function deleteConsumo(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este consumo?')) {
        try {
            await consumosAPI.delete(id);
            showNotification('Consumo eliminado correctamente', 'success');
            loadConsumos();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadConsumos);
</script>
@endsection
