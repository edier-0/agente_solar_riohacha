<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Prediccion;
use Illuminate\Http\Request;

class PrediccionController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Prediccion::with('empresa')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'empresa_id' => 'required|exists:empresas,id',
            'fecha' => 'required|date',
            'produccion_solar_esperada' => 'sometimes|numeric',
            'consumo_futuro' => 'sometimes|numeric',
            'costos_aproximados' => 'sometimes|numeric',
            'riesgo_sobrecarga' => 'sometimes|boolean',
            'riesgo_apagon' => 'sometimes|boolean',
        ]);

        $prediccion = Prediccion::create($validated);
        return response()->json($prediccion->load('empresa'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $prediccion = Prediccion::with('empresa')->findOrFail($id);
        return response()->json($prediccion, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $prediccion = Prediccion::findOrFail($id);

        $validated = $request->validate([
            'empresa_id' => 'sometimes|exists:empresas,id',
            'fecha' => 'sometimes|date',
            'produccion_solar_esperada' => 'sometimes|numeric',
            'consumo_futuro' => 'sometimes|numeric',
            'costos_aproximados' => 'sometimes|numeric',
            'riesgo_sobrecarga' => 'sometimes|boolean',
            'riesgo_apagon' => 'sometimes|boolean',
        ]);

        $prediccion->update($validated);
        return response()->json($prediccion->load('empresa'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $prediccion = Prediccion::findOrFail($id);
        $prediccion->delete();
        return response()->json(['message' => 'Predicción eliminada'], 200);
    }
}
