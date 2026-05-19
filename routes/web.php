<?php

use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Web\DashboardController;
use App\Http\Controllers\Web\EmpresaController;
use App\Http\Controllers\Web\ConsumoController;
use App\Http\Controllers\Web\RadiacionController;
use App\Http\Controllers\Web\AlertaController;
use App\Http\Controllers\Web\ReporteController;
use App\Http\Controllers\Web\UsuarioController;

/*
|--------------------------------------------------------------------------
| Web Routes
|--------------------------------------------------------------------------
|
| Here is where you can register web routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "web" middleware group. Make something great!
|
*/

// Ruta de inicio
Route::get('/', function () {
    return redirect()->route('dashboard');
});

// Dashboard
Route::get('/dashboard', [DashboardController::class, 'index'])->name('dashboard');

// Empresas
Route::get('/empresas', [EmpresaController::class, 'index'])->name('empresas.index');
Route::get('/empresas/create', [EmpresaController::class, 'create'])->name('empresas.create');
Route::get('/empresas/{id}/edit', [EmpresaController::class, 'edit'])->name('empresas.edit');
Route::get('/empresas/{id}', [EmpresaController::class, 'show'])->name('empresas.show');

// Consumos
Route::get('/consumos', [ConsumoController::class, 'index'])->name('consumos.index');
Route::get('/consumos/create', [ConsumoController::class, 'create'])->name('consumos.create');
Route::get('/consumos/{id}/edit', [ConsumoController::class, 'edit'])->name('consumos.edit');

// Radiaciones
Route::get('/radiaciones', [RadiacionController::class, 'index'])->name('radiaciones.index');
Route::get('/radiaciones/create', [RadiacionController::class, 'create'])->name('radiaciones.create');
Route::get('/radiaciones/{id}/edit', [RadiacionController::class, 'edit'])->name('radiaciones.edit');

// Alertas
Route::get('/alertas', [AlertaController::class, 'index'])->name('alertas.index');
Route::get('/alertas/create', [AlertaController::class, 'create'])->name('alertas.create');

// Reportes
Route::get('/reportes', [ReporteController::class, 'index'])->name('reportes.index');
Route::get('/reportes/create', [ReporteController::class, 'create'])->name('reportes.create');
Route::get('/reportes/{id}/edit', [ReporteController::class, 'edit'])->name('reportes.edit');

// Usuarios
Route::get('/usuarios', [UsuarioController::class, 'index'])->name('usuarios.index');
Route::get('/usuarios/create', [UsuarioController::class, 'create'])->name('usuarios.create');
Route::get('/usuarios/{id}/edit', [UsuarioController::class, 'edit'])->name('usuarios.edit');
