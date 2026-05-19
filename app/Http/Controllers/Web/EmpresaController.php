<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;
use App\Models\Empresa;

class EmpresaController extends Controller
{
    public function index()
    {
        return view('empresas.index');
    }

    public function create()
    {
        return view('empresas.form');
    }

    public function edit($id)
    {
        $empresa = Empresa::findOrFail($id);
        return view('empresas.form', compact('empresa'));
    }

    public function show($id)
    {
        $empresa = Empresa::findOrFail($id);
        return view('empresas.show', compact('empresa'));
    }
}
