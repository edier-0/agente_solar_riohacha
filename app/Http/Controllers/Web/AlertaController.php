<?php

namespace App\Http\Controllers\Web;

use App\Http\Controllers\Controller;

class AlertaController extends Controller
{
    public function index()
    {
        return view('alertas.index');
    }

    public function create()
    {
        return view('alertas.create');
    }
}
