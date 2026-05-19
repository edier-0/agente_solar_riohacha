<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;

class ReporteController extends Controller
{
    public function index()
    {
        return view('reportes.index');
    }

    public function create()
    {
        return view('reportes.create');
    }

    public function edit($id)
    {
        return view('reportes.edit', compact('id'));
    }
}
