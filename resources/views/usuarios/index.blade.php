@extends('layouts.app')

@section('title', 'Usuarios - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/usuarios.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">Usuarios</h1>
    <div class="header-actions">
        <a href="{{ route('usuarios.create') }}" class="btn btn-primary">+ Nuevo Usuario</a>
    </div>
</div>

<div class="card">
    <div class="card-body">
        <table class="data-table" id="usuarios-table">
            <thead>
                <tr>
                    <th>Nombre</th>
                    <th>Email</th>
                    <th>Rol</th>
                    <th>Registrado</th>
                    <th>Acciones</th>
                </tr>
            </thead>
            <tbody id="usuarios-tbody">
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
async function loadUsuarios() {
    try {
        const usuarios = await usuariosAPI.getAll();
        const tbody = document.getElementById('usuarios-tbody');

        if (usuarios.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">No hay usuarios registrados</td>
                </tr>
            `;
        } else {
            tbody.innerHTML = usuarios.map(usuario => `
                <tr>
                    <td><strong>${usuario.nombre}</strong></td>
                    <td>${usuario.email}</td>
                    <td><span class="badge ${rolBadgeClass(usuario.rol)}">${usuario.rol}</span></td>
                    <td>${formatDate(usuario.created_at)}</td>
                    <td>
                        <div class="table-actions">
                            <a href="/usuarios/${usuario.id}/edit" class="table-action-btn">Editar</a>
                            <button class="table-action-btn danger" onclick="deleteUsuario(${usuario.id})">Eliminar</button>
                        </div>
                    </td>
                </tr>
            `).join('');
        }
    } catch (error) {
        showError(error);
    }
}

function rolBadgeClass(rol) {
    switch (rol) {
        case 'Administrador': return 'badge-error';
        case 'Analista energético': return 'badge-info';
        default: return 'badge-success';
    }
}

async function deleteUsuario(id) {
    if (confirm('¿Estás seguro de que deseas eliminar este usuario?')) {
        try {
            await usuariosAPI.delete(id);
            showNotification('Usuario eliminado correctamente', 'success');
            loadUsuarios();
        } catch (error) {
            showError(error);
        }
    }
}

document.addEventListener('DOMContentLoaded', loadUsuarios);
</script>
@endsection
