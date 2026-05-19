<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Recomendacion;
use Illuminate\Http\Request;

class RecomendacionController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Recomendacion::with('empresa')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'empresa_id' => 'required|exists:empresas,id',
            'fecha' => 'required|date',
            'recomendacion' => 'required|string',
        ]);

        $recomendacion = Recomendacion::create($validated);
        return response()->json($recomendacion->load('empresa'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $recomendacion = Recomendacion::with('empresa')->findOrFail($id);
        return response()->json($recomendacion, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $recomendacion = Recomendacion::findOrFail($id);

        $validated = $request->validate([
            'empresa_id' => 'sometimes|exists:empresas,id',
            'fecha' => 'sometimes|date',
            'recomendacion' => 'sometimes|string',
        ]);

        $recomendacion->update($validated);
        return response()->json($recomendacion->load('empresa'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $recomendacion = Recomendacion::findOrFail($id);
        $recomendacion->delete();
        return response()->json(['message' => 'Recomendación eliminada'], 200);
    }
}
