<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Recomendacion extends Model
{
    use HasFactory;

    protected $table = 'recomendaciones';

    protected $fillable = [
        'empresa_id',
        'fecha',
        'recomendacion',
    ];

    protected $casts = [
        'fecha' => 'date',
    ];

    public function empresa()
    {
        return $this->belongsTo(Empresa::class, 'empresa_id');
    }
}
