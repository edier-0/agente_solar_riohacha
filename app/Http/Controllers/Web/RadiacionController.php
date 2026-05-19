<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;

class RadiacionController extends Controller
{
    public function index()
    {
        return view('radiaciones.index');
    }

    public function create()
    {
        return view('radiaciones.create');
    }

    public function edit($id)
    {
        return view('radiaciones.edit', compact('id'));
    }
}
