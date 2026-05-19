<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Reporte extends Model
{
    use HasFactory;

    protected $table = 'reportes';

    protected $fillable = [
        'empresa_id',
        'fecha',
        'tipo',
        'nombre_archivo',
        'ruta_archivo',
    ];

    protected $casts = [
        'fecha' => 'date',
    ];

    public function empresa()
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
