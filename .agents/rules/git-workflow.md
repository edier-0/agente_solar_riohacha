# 🌿 Convención de Trabajo en Git

Reglas obligatorias de branching, commits y Pull Requests.

## 1. Estrategia de Ramas (Branching)
- **Prohibido trabajar directo en `main` o `develop`**.
- Cada tarea o requerimiento debe realizarse en su propia rama:
  - `feature/<nombre-tarea>`: Nuevas funcionalidades o vistas.
  - `fix/<nombre-tarea>`: Corrección de bugs o fallas de lógica.
  - `chore/<nombre-tarea>`: Tareas de mantenimiento, dependencias o docs.
  - `refactor/<nombre-tarea>`: Reestructuración de código sin alterar lógica.

## 2. Commits Atómicos
- Cada commit debe representar un cambio lógico único e indivisible.
- Seguir el estándar de **Conventional Commits**:
  - `feat: <descripción concisa>`
  - `fix: <descripción concisa>`
  - `docs: <descripción concisa>`
  - `chore: <descripción concisa>`
  - `refactor: <descripción concisa>`
- Mensajes en español o inglés, imperativos y claros.

## 3. Protocolo de Pull Request (PR) y Merge
- **Esperar orden del usuario**: El agente nunca crea un PR ni fusiona
  ramas de forma autónoma.
- El usuario debe ordenar explícitamente:
  - A qué rama objetivo (`develop`, `main`, etc.) se dirigirá el PR.
  - Cuándo se procede a publicar o solicitar la integración.
- Antes de solicitar la orden de PR:
  - Verificar que el árbol de trabajo esté limpio (`git status`).
  - Validar que no existan errores de sintaxis o tests rotos.
