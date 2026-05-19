<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\ConsumoEnergetico;
use Illuminate\Http\Request;

class ConsumoEnergeticoController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(ConsumoEnergetico::with('empresa')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'empresa_id' => 'required|exists:empresas,id',
            'fecha' => 'required|date',
            'consumo_horas' => 'sometimes|array',
            'consumo_diario' => 'sometimes|numeric',
            'tarifa' => 'sometimes|numeric',
        ]);

        $consumo = ConsumoEnergetico::create($validated);
        return response()->json($consumo->load('empresa'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $consumo = ConsumoEnergetico::with('empresa')->findOrFail($id);
        return response()->json($consumo, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $consumo = ConsumoEnergetico::findOrFail($id);

        $validated = $request->validate([
            'empresa_id' => 'sometimes|exists:empresas,id',
            'fecha' => 'sometimes|date',
            'consumo_horas' => 'sometimes|array',
            'consumo_diario' => 'sometimes|numeric',
            'tarifa' => 'sometimes|numeric',
        ]);

        $consumo->update($validated);
        return response()->json($consumo->load('empresa'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $consumo = ConsumoEnergetico::findOrFail($id);
        $consumo->delete();
        return response()->json(['message' => 'Consumo eliminado'], 200);
    }
}
