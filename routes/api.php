<?php

use Illuminate\Http\Request;
use Illuminate\Support\Facades\Route;
use App\Http\Controllers\Api\UsuarioController;
use App\Http\Controllers\Api\EmpresaController;
use App\Http\Controllers\Api\ConsumoEnergeticoController;
use App\Http\Controllers\Api\RadiacionSolarController;
use App\Http\Controllers\Api\RecomendacionController;
use App\Http\Controllers\Api\AlertaController;
use App\Http\Controllers\Api\ReporteController;
use App\Http\Controllers\Api\PrediccionController;

/*
|--------------------------------------------------------------------------
| API Routes
|--------------------------------------------------------------------------
|
| Here is where you can register API routes for your application. These
| routes are loaded by the RouteServiceProvider and all of them will
| be assigned to the "api" middleware group. Make something great!
|
*/

// Rutas de recursos API
Route::apiResource('usuarios', UsuarioController::class);
Route::apiResource('empresas', EmpresaController::class);
Route::apiResource('consumos', ConsumoEnergeticoController::class);
Route::apiResource('radiaciones', RadiacionSolarController::class);
Route::apiResource('recomendaciones', RecomendacionController::class);
Route::apiResource('alertas', AlertaController::class);
Route::apiResource('reportes', ReporteController::class);
Route::apiResource('predicciones', PrediccionController::class);

Route::middleware('auth:sanctum')->get('/user', function (Request $request) {
    return $request->user();
});
