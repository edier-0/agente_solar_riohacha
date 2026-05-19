<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Alerta;
use Illuminate\Http\Request;

class AlertaController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Alerta::with('empresa')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'empresa_id' => 'required|exists:empresas,id',
            'tipo_alerta' => 'required|string',
            'mensaje' => 'required|string',
        ]);

        $alerta = Alerta::create($validated);
        return response()->json($alerta->load('empresa'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $alerta = Alerta::with('empresa')->findOrFail($id);
        return response()->json($alerta, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $alerta = Alerta::findOrFail($id);

        $validated = $request->validate([
            'empresa_id' => 'sometimes|exists:empresas,id',
            'tipo_alerta' => 'sometimes|string',
            'mensaje' => 'sometimes|string',
        ]);

        $alerta->update($validated);
        return response()->json($alerta->load('empresa'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $alerta = Alerta::findOrFail($id);
        $alerta->delete();
        return response()->json(['message' => 'Alerta eliminada'], 200);
    }
}
