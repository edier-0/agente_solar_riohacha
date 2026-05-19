<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class Usuario extends Model
{
    use HasFactory;

    protected $table = 'usuarios';

    protected $fillable = [
        'nombre',
        'email',
        'contraseña',
        'rol',
    ];

    protected $hidden = [
        'contraseña',
    ];

    public function empresas()
    {
        return $this->hasMany(Empresa::class, 'usuario_id');
    }
}
