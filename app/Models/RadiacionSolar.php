<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;

class RadiacionSolar extends Model
{
    use HasFactory;

    protected $table = 'radiacionsolar';

    protected $fillable = [
        'fecha',
        'radiacion_historica',
        'radiacion_actual',
        'temperatura',
        'nubosidad',
        'clima',
    ];

    protected $casts = [
        'fecha' => 'date',
    ];
}
