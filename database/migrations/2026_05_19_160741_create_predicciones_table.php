<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    /**
     * Run the migrations.
     */
    public function up(): void
    {
        Schema::create('predicciones', function (Blueprint $table) {
            $table->id();
            $table->foreignId('empresa_id')->constrained('empresas')->onDelete('cascade');
            $table->date('fecha');
            $table->decimal('produccion_solar_esperada', 12, 4)->nullable();
            $table->decimal('consumo_futuro', 12, 4)->nullable();
            $table->decimal('costos_aproximados', 15, 2)->nullable();
            $table->boolean('riesgo_sobrecarga')->default(false);
            $table->boolean('riesgo_apagon')->default(false);
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('predicciones');
    }
};
