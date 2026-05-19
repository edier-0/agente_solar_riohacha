<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;

class ConsumoController extends Controller
{
    public function index()
    {
        return view('consumos.index');
    }

    public function create()
    {
        return view('consumos.create');
    }

    public function edit($id)
    {
        return view('consumos.edit', compact('id'));
    }
}
