@extends('layouts.app')

@section('title', (isset($empresa) ? 'Editar' : 'Nueva') . ' Empresa - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/empresas.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">{{ isset($empresa) ? 'Editar Empresa' : 'Nueva Empresa' }}</h1>
</div>

<div class="empresa-form-wrapper">
<div class="form-card">
    <form id="empresa-form">
        <div class="form-group">
            <label for="nombre">Nombre de la Empresa *</label>
            <input type="text" id="nombre" name="nombre" required 
                   value="{{ $empresa->nombre ?? '' }}" placeholder="Ej: Hielera El Ártico">
        </div>
        
        <div class="form-group">
            <label for="tipo">Tipo de Empresa *</label>
            <select id="tipo" name="tipo" required>
                <option value="">Seleccionar tipo...</option>
                <option value="Hotel" {{ isset($empresa) && $empresa->tipo === 'Hotel' ? 'selected' : '' }}>Hotel</option>
                <option value="Hielera" {{ isset($empresa) && $empresa->tipo === 'Hielera' ? 'selected' : '' }}>Hielera</option>
                <option value="Retail" {{ isset($empresa) && $empresa->tipo === 'Retail' ? 'selected' : '' }}>Retail</option>
                <option value="PYME" {{ isset($empresa) && $empresa->tipo === 'PYME' ? 'selected' : '' }}>PYME</option>
                <option value="Comunidad" {{ isset($empresa) && $empresa->tipo === 'Comunidad' ? 'selected' : '' }}>Comunidad</option>
            </select>
        </div>
        
        <div class="form-group">
            <label for="usuario_id">Usuario Responsable *</label>
            <select id="usuario_id" name="usuario_id" required>
                <option value="">Seleccionar usuario...</option>
                <!-- Los usuarios se cargarán dinámicamente -->
            </select>
        </div>
        
        <div class="form-actions">
            <button type="submit" class="btn btn-primary">{{ isset($empresa) ? 'Actualizar' : 'Crear' }} Empresa</button>
            <a href="{{ route('empresas.index') }}" class="btn btn-secondary">Cancelar</a>
        </div>
    </form>
</div>
</div>
@endsection

@section('scripts')
<script>
async function loadUsuarios() {
    try {
        const usuarios = await usuariosAPI.getAll();
        const select = document.getElementById('usuario_id');
        
        usuarios.forEach(usuario => {
            const option = document.createElement('option');
            option.value = usuario.id;
            option.textContent = usuario.nombre;
            {{ isset($empresa) && 'selected' }} = usuario.id === {{ isset($empresa) ? $empresa->usuario_id : 'null' }};
            select.appendChild(option);
        });
    } catch (error) {
        showError(error);
    }
}

document.getElementById('empresa-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = {
        nombre: document.getElementById('nombre').value,
        tipo: document.getElementById('tipo').value,
        usuario_id: parseInt(document.getElementById('usuario_id').value),
    };
    
    try {
        {{ isset($empresa) ? 'await empresasAPI.update(' . $empresa->id . ', formData);' : 'await empresasAPI.create(formData);' }}
        showNotification('Empresa {{ isset($empresa) ? 'actualizada' : 'creada' }} correctamente', 'success');
        window.location.href = '{{ route("empresas.index") }}';
    } catch (error) {
        showError(error);
    }
});

document.addEventListener('DOMContentLoaded', loadUsuarios);
</script>
@endsection
