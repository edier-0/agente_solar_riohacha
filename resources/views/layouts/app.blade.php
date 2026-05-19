<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'Agente Solar Riohacha')</title>
    
    <!-- Estilos CSS -->
    <link rel="stylesheet" href="{{ asset('css/global.css') }}">
    <link rel="stylesheet" href="{{ asset('css/layouts/sidebar.css') }}">
    <link rel="stylesheet" href="{{ asset('css/components/cards.css') }}">
    <link rel="stylesheet" href="{{ asset('css/components/tables.css') }}">
    @yield('styles')
</head>
<body>
    <!-- Mobile Header -->
    <header class="mobile-header">
        <div class="mobile-logo">
            <span>☀️</span>
            <span>Solar</span>
        </div>
        <button class="hamburger-btn" id="hamburger-btn" aria-label="Abrir menú" aria-expanded="false">
            <span></span>
            <span></span>
            <span></span>
        </button>
    </header>

    <!-- Overlay -->
    <div class="sidebar-overlay" id="sidebar-overlay"></div>

    <div class="app-layout">
        <!-- Sidebar -->
        <aside class="sidebar" id="sidebar">
            <div class="sidebar-header">
                <div class="sidebar-logo">
                    <div class="sidebar-logo-icon">☀️</div>
                    <span>Solar</span>
                </div>
            </div>
            
            <nav>
                <ul class="sidebar-nav">
                    <li class="sidebar-nav-item">
                        <a href="{{ route('dashboard') }}" class="sidebar-nav-link {{ request()->routeIs('dashboard') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">📊</span>
                            <span>Dashboard</span>
                        </a>
                    </li>
                    <li class="sidebar-nav-item">
                        <a href="{{ route('empresas.index') }}" class="sidebar-nav-link {{ request()->routeIs('empresas.*') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">🏢</span>
                            <span>Empresas</span>
                        </a>
                    </li>
                    <li class="sidebar-nav-item">
                        <a href="{{ route('consumos.index') }}" class="sidebar-nav-link {{ request()->routeIs('consumos.*') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">⚡</span>
                            <span>Consumos</span>
                        </a>
                    </li>
                    <li class="sidebar-nav-item">
                        <a href="{{ route('radiaciones.index') }}" class="sidebar-nav-link {{ request()->routeIs('radiaciones.*') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">☀️</span>
                            <span>Radiación Solar</span>
                        </a>
                    </li>
                    <li class="sidebar-nav-item">
                        <a href="{{ route('alertas.index') }}" class="sidebar-nav-link {{ request()->routeIs('alertas.*') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">🚨</span>
                            <span>Alertas</span>
                        </a>
                    </li>
                    <li class="sidebar-nav-item">
                        <a href="{{ route('reportes.index') }}" class="sidebar-nav-link {{ request()->routeIs('reportes.*') ? 'active' : '' }}">
                            <span class="sidebar-nav-icon">📄</span>
                            <span>Reportes</span>
                        </a>
                    </li>
                </ul>
            </nav>
        </aside>
        
        <!-- Main Content -->
        <main class="main-content">
            @yield('content')
        </main>
    </div>
    
    <!-- Scripts -->
    <script src="{{ asset('js/api.js') }}"></script>
    <script>
        // Toggle sidebar en móvil
        (function () {
            const btn = document.getElementById('hamburger-btn');
            const sidebar = document.getElementById('sidebar');
            const overlay = document.getElementById('sidebar-overlay');

            function openSidebar() {
                sidebar.classList.add('open');
                overlay.classList.add('active');
                btn.classList.add('open');
                btn.setAttribute('aria-expanded', 'true');
                document.body.style.overflow = 'hidden';
            }

            function closeSidebar() {
                sidebar.classList.remove('open');
                overlay.classList.remove('active');
                btn.classList.remove('open');
                btn.setAttribute('aria-expanded', 'false');
                document.body.style.overflow = '';
            }

            btn.addEventListener('click', function () {
                sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
            });

            overlay.addEventListener('click', closeSidebar);

            // Cerrar al hacer clic en un link del sidebar (navegación móvil)
            sidebar.querySelectorAll('.sidebar-nav-link').forEach(function (link) {
                link.addEventListener('click', closeSidebar);
            });
        }());
    </script>
    @yield('scripts')
</body>
</html>
