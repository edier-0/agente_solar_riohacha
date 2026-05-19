/* ============================================================
   API Client - Agente Solar Riohacha
   ============================================================ */

const API_BASE_URL = '/api';

/**
 * Función auxiliar para hacer peticiones a la API
 */
async function apiRequest(endpoint, method = 'GET', data = null) {
  const options = {
    method: method,
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
  };

  if (data && method !== 'GET') {
    options.body = JSON.stringify(data);
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
    
    if (!response.ok) {
      throw new Error(`Error ${response.status}: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

/* ============================================================
   Usuarios
   ============================================================ */
const usuariosAPI = {
  getAll: () => apiRequest('/usuarios'),
  getById: (id) => apiRequest(`/usuarios/${id}`),
  create: (data) => apiRequest('/usuarios', 'POST', data),
  update: (id, data) => apiRequest(`/usuarios/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/usuarios/${id}`, 'DELETE'),
};

/* ============================================================
   Empresas
   ============================================================ */
const empresasAPI = {
  getAll: () => apiRequest('/empresas'),
  getById: (id) => apiRequest(`/empresas/${id}`),
  create: (data) => apiRequest('/empresas', 'POST', data),
  update: (id, data) => apiRequest(`/empresas/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/empresas/${id}`, 'DELETE'),
};

/* ============================================================
   Consumo Energético
   ============================================================ */
const consumosAPI = {
  getAll: () => apiRequest('/consumos'),
  getById: (id) => apiRequest(`/consumos/${id}`),
  create: (data) => apiRequest('/consumos', 'POST', data),
  update: (id, data) => apiRequest(`/consumos/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/consumos/${id}`, 'DELETE'),
};

/* ============================================================
   Radiación Solar
   ============================================================ */
const radiacionesAPI = {
  getAll: () => apiRequest('/radiaciones'),
  getById: (id) => apiRequest(`/radiaciones/${id}`),
  create: (data) => apiRequest('/radiaciones', 'POST', data),
  update: (id, data) => apiRequest(`/radiaciones/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/radiaciones/${id}`, 'DELETE'),
};

/* ============================================================
   Recomendaciones
   ============================================================ */
const recomendacionesAPI = {
  getAll: () => apiRequest('/recomendaciones'),
  getById: (id) => apiRequest(`/recomendaciones/${id}`),
  create: (data) => apiRequest('/recomendaciones', 'POST', data),
  update: (id, data) => apiRequest(`/recomendaciones/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/recomendaciones/${id}`, 'DELETE'),
};

/* ============================================================
   Alertas
   ============================================================ */
const alertasAPI = {
  getAll: () => apiRequest('/alertas'),
  getById: (id) => apiRequest(`/alertas/${id}`),
  create: (data) => apiRequest('/alertas', 'POST', data),
  update: (id, data) => apiRequest(`/alertas/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/alertas/${id}`, 'DELETE'),
};

/* ============================================================
   Reportes
   ============================================================ */
const reportesAPI = {
  getAll: () => apiRequest('/reportes'),
  getById: (id) => apiRequest(`/reportes/${id}`),
  create: (data) => apiRequest('/reportes', 'POST', data),
  update: (id, data) => apiRequest(`/reportes/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/reportes/${id}`, 'DELETE'),
};

/* ============================================================
   Predicciones
   ============================================================ */
const prediccionesAPI = {
  getAll: () => apiRequest('/predicciones'),
  getById: (id) => apiRequest(`/predicciones/${id}`),
  create: (data) => apiRequest('/predicciones', 'POST', data),
  update: (id, data) => apiRequest(`/predicciones/${id}`, 'PUT', data),
  delete: (id) => apiRequest(`/predicciones/${id}`, 'DELETE'),
};

/* ============================================================
   Utilidades de UI
   ============================================================ */
function showNotification(message, type = 'info') {
  console.log(`[${type.toUpperCase()}] ${message}`);
  // Aquí se puede implementar un sistema de notificaciones visual
}

function showError(error) {
  console.error('Error:', error);
  showNotification(error.message || 'Ocurrió un error', 'error');
}

function formatDate(dateString) {
  const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
  return new Date(dateString).toLocaleDateString('es-ES', options);
}

function formatCurrency(value) {
  return new Intl.NumberFormat('es-ES', {
    style: 'currency',
    currency: 'COP',
  }).format(value);
}
