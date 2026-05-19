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
        Schema::create('radiacionsolar', function (Blueprint $table) {
            $table->id();
            $table->date('fecha');
            $table->decimal('radiacion_historica', 10, 4)->nullable();
            $table->decimal('radiacion_actual', 10, 4)->nullable();
            $table->decimal('temperatura', 5, 2)->nullable();
            $table->decimal('nubosidad', 5, 2)->nullable();
            $table->string('clima')->nullable();
            $table->timestamps();
        });
    }

    /**
     * Reverse the migrations.
     */
    public function down(): void
    {
        Schema::dropIfExists('radiacionsolar');
    }
};
