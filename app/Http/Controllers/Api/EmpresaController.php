<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Empresa;
use Illuminate\Http\Request;

class EmpresaController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Empresa::with('usuario')->get(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'nombre' => 'required|string|max:255',
            'tipo' => 'required|in:Hotel,Hielera,Retail,PYME,Comunidad',
            'usuario_id' => 'required|exists:usuarios,id',
        ]);

        $empresa = Empresa::create($validated);
        return response()->json($empresa->load('usuario'), 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $empresa = Empresa::with('usuario', 'consumos', 'recomendaciones', 'alertas', 'reportes', 'predicciones')->findOrFail($id);
        return response()->json($empresa, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $empresa = Empresa::findOrFail($id);

        $validated = $request->validate([
            'nombre' => 'sometimes|string|max:255',
            'tipo' => 'sometimes|in:Hotel,Hielera,Retail,PYME,Comunidad',
            'usuario_id' => 'sometimes|exists:usuarios,id',
        ]);

        $empresa->update($validated);
        return response()->json($empresa->load('usuario'), 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $empresa = Empresa::findOrFail($id);
        $empresa->delete();
        return response()->json(['message' => 'Empresa eliminada'], 200);
    }
}
