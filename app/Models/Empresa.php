<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Empresa extends Model
{
    use HasFactory;

    protected $table = 'empresas';

    protected $fillable = [
        'nombre',
        'tipo',
        'usuario_id',
    ];

    public function usuario()
    {
        return $this->belongsTo(Usuario::class, 'usuario_id');
    }

    public function consumos()
    {
        return $this->hasMany(ConsumoEnergetico::class, 'empresa_id');
    }

    public function recomendaciones()
    {
        return $this->hasMany(Recomendacion::class, 'empresa_id');
    }

    public function alertas()
    {
        return $this->hasMany(Alerta::class, 'empresa_id');
    }

    public function reportes()
    {
        return $this->hasMany(Reporte::class, 'empresa_id');
    }

    public function predicciones()
    {
        return $this->hasMany(Prediccion::class, 'empresa_id');
    }
}
