<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Prediccion extends Model
{
    use HasFactory;

    protected $table = 'predicciones';

    protected $fillable = [
        'empresa_id',
        'fecha',
        'produccion_solar_esperada',
        'consumo_futuro',
        'costos_aproximados',
        'riesgo_sobrecarga',
        'riesgo_apagon',
    ];

    protected $casts = [
        'fecha' => 'date',
        'riesgo_sobrecarga' => 'boolean',
        'riesgo_apagon' => 'boolean',
    ];

    public function empresa()
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
