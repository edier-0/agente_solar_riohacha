<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\RadiacionSolar;
use Illuminate\Http\Request;

class RadiacionSolarController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(RadiacionSolar::all(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'fecha' => 'required|date',
            'radiacion_historica' => 'sometimes|numeric',
            'radiacion_actual' => 'sometimes|numeric',
            'temperatura' => 'sometimes|numeric',
            'nubosidad' => 'sometimes|numeric',
            'clima' => 'sometimes|string',
        ]);

        $radiacion = RadiacionSolar::create($validated);
        return response()->json($radiacion, 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $radiacion = RadiacionSolar::findOrFail($id);
        return response()->json($radiacion, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $radiacion = RadiacionSolar::findOrFail($id);

        $validated = $request->validate([
            'fecha' => 'sometimes|date',
            'radiacion_historica' => 'sometimes|numeric',
            'radiacion_actual' => 'sometimes|numeric',
            'temperatura' => 'sometimes|numeric',
            'nubosidad' => 'sometimes|numeric',
            'clima' => 'sometimes|string',
        ]);

        $radiacion->update($validated);
        return response()->json($radiacion, 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $radiacion = RadiacionSolar::findOrFail($id);
        $radiacion->delete();
        return response()->json(['message' => 'Radiación eliminada'], 200);
    }
}
