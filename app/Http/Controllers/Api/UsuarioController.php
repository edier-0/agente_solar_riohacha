<?php

namespace App\Http\Controllers\Api;

use App\Http\Controllers\Controller;
use App\Models\Usuario;
use Illuminate\Http\Request;

class UsuarioController extends Controller
{
    /**
     * Display a listing of the resource.
     */
    public function index()
    {
        return response()->json(Usuario::all(), 200);
    }

    /**
     * Store a newly created resource in storage.
     */
    public function store(Request $request)
    {
        $validated = $request->validate([
            'nombre' => 'required|string|max:255',
            'email' => 'required|email|unique:usuarios',
            'contraseña' => 'required|string|min:6',
            'rol' => 'required|in:Administrador,Empresa cliente,Analista energético',
        ]);

        $usuario = Usuario::create($validated);
        return response()->json($usuario, 201);
    }

    /**
     * Display the specified resource.
     */
    public function show(string $id)
    {
        $usuario = Usuario::findOrFail($id);
        return response()->json($usuario, 200);
    }

    /**
     * Update the specified resource in storage.
     */
    public function update(Request $request, string $id)
    {
        $usuario = Usuario::findOrFail($id);

        $validated = $request->validate([
            'nombre' => 'sometimes|string|max:255',
            'email' => 'sometimes|email|unique:usuarios,email,' . $id,
            'contraseña' => 'sometimes|string|min:6',
            'rol' => 'sometimes|in:Administrador,Empresa cliente,Analista energético',
        ]);

        $usuario->update($validated);
        return response()->json($usuario, 200);
    }

    /**
     * Remove the specified resource from storage.
     */
    public function destroy(string $id)
    {
        $usuario = Usuario::findOrFail($id);
        $usuario->delete();
        return response()->json(['message' => 'Usuario eliminado'], 200);
    }
}
