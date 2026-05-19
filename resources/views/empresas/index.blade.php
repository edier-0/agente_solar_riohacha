@extends('layouts.app')

@section('title', 'Empresas - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/empresas.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Empresas</h1>
    <div class="header-actions">
        <a href="{{ route('empresas.create') }}" class="btn btn-primary">+ Nueva Empresa</a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <table class="data-table" id="empresas-table">
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Usuario</th>
                    <th>Creada</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="empresas-tbody">
                <tr>
                    <td colspan="5" class="text-center text-muted">Cargando...</td>
                </tr>
            </tbody>
        </table>
    </div>
</div>
@endsection

@section('scripts')
<script>
async function loadEmpresas() {
    try {
        const empresas = await empresasAPI.getAll();
        const tbody = document.getElementById('empresas-tbody');
        
        if (empresas.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">No hay empresas registradas</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = empresas.map(empresa => `
                <tr>
                    <td><strong>${empresa.nombre}</strong></td>
                    <td><span class="badge badge-info">${empresa.tipo}</span></td>
                    <td>${empresa.usuario?.nombre || 'N/A'}</td>
                    <td>${formatDate(empresa.created_at)}</td>
                    <td>
                        <div class="table-actions">
                            <a href="/empresas/${empresa.id}" class="table-action-btn">Ver</a>
                            <a href="/empresas/${empresa.id}/edit" class="table-action-btn">Editar</a>
                            <button class="table-action-btn danger" onclick="deleteEmpresa(${empresa.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showError(error);
    }
}

async function deleteEmpresa(id) {
    if (confirm('¿Estás seguro de que deseas eliminar esta empresa?')) {
        try {
            await empresasAPI.delete(id);
            showNotification('Empresa eliminada correctamente', 'success');
            loadEmpresas();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadEmpresas);
</script>
@endsection
