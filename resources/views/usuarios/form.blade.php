@extends('layouts.app')

@section('title', (isset($usuario) ? 'Editar' : 'Nuevo') . ' Usuario - Agente Solar Riohacha')

@section('styles')
<link rel="stylesheet" href="{{ asset('css/views/usuarios.css') }}">
@endsection

@section('content')
<div class="header">
    <h1 class="header-title">{{ isset($usuario) ? 'Editar Usuario' : 'Nuevo Usuario' }}</h1>
</div>

<div class="usuario-form-wrapper">
    <div class="form-card">
        <form id="usuario-form">
            <div class="form-group">
                <label for="nombre">Nombre completo *</label>
                <input type="text" id="nombre" name="nombre" required
                       value="{{ $usuario->nombre ?? '' }}" placeholder="Ej: Carlos Martínez">
            </div>

            <div class="form-group">
                <label for="email">Correo electrónico *</label>
                <input type="email" id="email" name="email" required
                       value="{{ $usuario->email ?? '' }}" placeholder="correo@ejemplo.com">
            </div>

            <div class="form-group">
                <label for="contraseña">
                    {{ isset($usuario) ? 'Nueva contraseña (dejar vacío para no cambiar)' : 'Contraseña *' }}
                </label>
                <input type="password" id="contraseña" name="contraseña"
                       {{ isset($usuario) ? '' : 'required' }}
                       placeholder="Mínimo 6 caracteres" minlength="6">
            </div>

            <div class="form-group">
                <label for="rol">Rol *</label>
                <select id="rol" name="rol" required>
                    <option value="">Seleccionar rol...</option>
                    <option value="Administrador"
                        {{ isset($usuario) && $usuario->rol === 'Administrador' ? 'selected' : '' }}>
                        Administrador
                    </option>
                    <option value="Empresa cliente"
                        {{ isset($usuario) && $usuario->rol === 'Empresa cliente' ? 'selected' : '' }}>
                        Empresa cliente
                    </option>
                    <option value="Analista energético"
                        {{ isset($usuario) && $usuario->rol === 'Analista energético' ? 'selected' : '' }}>
                        Analista energético
                    </option>
                </select>
            </div>

            <div id="form-error" class="alert alert-error" style="display:none;"></div>

            <div class="form-actions">
                <button type="submit" class="btn btn-primary">
                    {{ isset($usuario) ? 'Actualizar' : 'Crear' }} Usuario
                </button>
                <a href="{{ route('usuarios.index') }}" class="btn btn-secondary">Cancelar</a>
            </div>
        </form>
    </div>
</div>
@endsection

@section('scripts')
<script>
document.getElementById('usuario-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const contraseña = document.getElementById('contraseña').value;

    const formData = {
        nombre: document.getElementById('nombre').value,
        email: document.getElementById('email').value,
        rol: document.getElementById('rol').value,
    };

    if (contraseña) {
        formData.contraseña = contraseña;
    }

    const errorDiv = document.getElementById('form-error');
    errorDiv.style.display = 'none';

    try {
        @if(isset($usuario))
            await usuariosAPI.update({{ $usuario->id }}, formData);
            showNotification('Usuario actualizado correctamente', 'success');
        @else
            if (!contraseña) {
                errorDiv.textContent = 'La contraseña es obligatoria para crear un usuario.';
                errorDiv.style.display = 'flex';
                return;
            }
            await usuariosAPI.create(formData);
            showNotification('Usuario creado correctamente', 'success');
        @endif
        window.location.href = '{{ route("usuarios.index") }}';
    } catch (error) {
        const msg = error?.message || 'Error al guardar el usuario.';
        errorDiv.textContent = msg;
        errorDiv.style.display = 'flex';
    }
});
</script>
@endsection
