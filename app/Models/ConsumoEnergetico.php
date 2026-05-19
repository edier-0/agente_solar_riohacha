<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class ConsumoEnergetico extends Model
{
    use HasFactory;

    protected $table = 'consumoenergetico';

    protected $fillable = [
        'empresa_id',
        'fecha',
        'consumo_horas',
        'consumo_diario',
        'tarifa',
    ];

    protected $casts = [
        'consumo_horas' => 'array',
        'fecha' => 'date',
    ];

    public function empresa()
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
