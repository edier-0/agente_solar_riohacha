<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Reporte;
use Illuminate\Http\Request;

class ReporteController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Reporte::with('empresa')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'empresa_id' => 'required|exists:empresas,id',
            'fecha' => 'required|date',
            'tipo' => 'required|in:PDF,Excel',
            'nombre_archivo' => 'sometimes|string',
            'ruta_archivo' => 'sometimes|string',
        ]);

        $reporte = Reporte::create($validated);
        return response()->json($reporte->load('empresa'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $reporte = Reporte::with('empresa')->findOrFail($id);
        return response()->json($reporte, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $reporte = Reporte::findOrFail($id);

        $validated = $request->validate([
            'empresa_id' => 'sometimes|exists:empresas,id',
            'fecha' => 'sometimes|date',
            'tipo' => 'sometimes|in:PDF,Excel',
            'nombre_archivo' => 'sometimes|string',
            'ruta_archivo' => 'sometimes|string',
        ]);

        $reporte->update($validated);
        return response()->json($reporte->load('empresa'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $reporte = Reporte::findOrFail($id);
        $reporte->delete();
        return response()->json(['message' => 'Reporte eliminado'], 200);
    }
}
