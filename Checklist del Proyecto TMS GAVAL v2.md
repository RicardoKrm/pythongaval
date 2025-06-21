Checklist del Proyecto TMS GAVAL v2.0 (Estado Actual)

✅ I. Arquitectura y Base del Proyecto
Configuración del Entorno: Proyecto Django (tms_gaval_final) con entorno virtual (venv) aislado.
Base de Datos: Conectado y funcionando con PostgreSQL.
Arquitectura Multi-Tenant: Implementada con django-tenants, permitiendo que múltiples empresas usen el sistema de forma segura y aislada.
Gestión de Tenants: Creado un tenant public para la administración global y un tenant de ejemplo (santarosa).
Sistema de Autenticación Funcional:
Superusuario global (superadmin o gaval) para gestionar todo el sistema.
Usuarios específicos por tenant (ej. ricardo para santarosa).
Acceso seguro y aislado a través de subdominios (santarosa.localhost:8000).

✅ II. Modelos de Datos (El Cerebro del Sistema)
Catálogos Completos:
Vehiculo y ModeloVehiculo.
Tarea (con costo y horas-hombre).
Insumo (con precio y categoría).
Proveedor.
Personal.
TipoFalla (con criticidad y causa para análisis de Pareto).
Lógica de Mantenimiento:
PautaMantenimiento (asocia tareas y KM a un modelo).
OrdenDeTrabajo (OT) como entidad central, con relaciones a todos los catálogos.
Folio Automático: Las OTs generan un folio único al crearse.
Cálculo de Costos Automático: El costo total de una OT se actualiza al añadir tareas o insumos.
Modelo para KPIs:
BitacoraDiaria para registrar horas operativas, de mantenimiento y de falla.

✅ III. Funcionalidades para el Usuario Final
Dashboard de Flota / Pizarra de Mantenimiento:
Muestra toda la flota del tenant.
Calcula y muestra automáticamente la próxima pauta de mantenimiento.
Usa alertas de color (NORMAL, PROXIMO, VENCIDO) para una rápida visualización.
Gestión de Órdenes de Trabajo (OT):
Página para listar todas las OTs, ordenadas por fecha.
Formulario para crear nuevas OTs (Preventivas y Correctivas).
Página de detalle para cada OT individual.
Funcionalidad para añadir tareas a una OT existente.
Funcionalidad para añadir insumos a una OT existente.
Funcionalidad para cambiar el estado de una OT (Pendiente, En Proceso, Finalizada).
Generación de Reportes:
Botón para generar un PDF profesional y limpio de cada Orden de Trabajo.
Registro de Datos de KPIs:
Página y formulario para la Bitácora Diaria, permitiendo el registro de horas.
Mejoras de Experiencia de Usuario (UX):
Notificaciones de éxito al crear o modificar datos.
Menús desplegables informativos (ej. para seleccionar vehículos).
Navegación clara con una barra de menú y botones para volver.

✅ IV. Dashboards de Inteligencia de Negocio
Dashboard de Indicadores KPI:
Filtro por rango de fechas.
Gráfico de Disponibilidad Mensual.
Gráfico de Confiabilidad Mensual.
Gráfico de Utilización Mensual.
Gráficos de donut para ver el estado de avance de OTs (Preventivas vs. Correctivas, Finalizadas vs. Pendientes).
Dashboard de Análisis de Fallas:
Diagrama de Pareto (gráfico de barras y línea) para identificar las fallas más frecuentes.
Tabla de datos detallada con frecuencias relativas y acumuladas.
Dashboard de Costos y Tendencias:
Tabla de Análisis de Costo Total de Propiedad (TCO) por proveedor, incluyendo $/KM.
Gráficos de líneas mostrando la evolución mensual de OTs creadas y finalizadas.


⏳ Parte 2: Funcionalidades Solicitadas por el Cliente (Lo que falta por hacer)

Gestión de Pautas Avanzada:
Carga de Pautas desde PDF: Crear una interfaz donde el cliente pueda subir un PDF de una pauta de mantenimiento y el sistema extraiga las tareas para crear o actualizar la PautaMantenimiento en la base de datos. (Esta es una funcionalidad avanzada que requiere OCR o parsing de PDF).
Administración Multi-Tenant para el Superadmin:
Panel de Creación de Empresas: Una interfaz para que el Superadmin (gaval) pueda crear nuevos clientes (tenants) y asignarles sus dominios desde la aplicación, sin usar el shell.
Gestión de Usuarios y Permisos:
Sistema de Roles y Permisos: Implementar un sistema de roles (ej. Administrador, Supervisor, Mecánico, Asistente) dentro de cada tenant.
Restricción de Vistas por Rol: Asegurar que un "Mecánico" solo vea las OTs que tiene asignadas, mientras que un "Supervisor" vea todas las de su equipo, y un "Administrador" vea todo lo de su empresa.
Autoservicio para Empresas Cliente:
Importación de Datos Masivos: Crear una interfaz para que los administradores de cada empresa puedan subir sus propios archivos Excel (vehículos, personal, etc.) para poblar o actualizar sus catálogos.
Funcionalidades de Usuario Estándar:
Página y Formulario de Login Personalizado: Reemplazar el login del admin de Django por una página de inicio de sesión con el branding de la aplicación.
Botón y Vista de "Cerrar Sesión".
Página de "Mi Perfil": Un lugar donde cada usuario pueda ver sus datos y, eventualmente, cambiar su contraseña.
Interfaz y Experiencia de Usuario (UX):
Modo Claro / Modo Nocturno: Un interruptor para que el usuario elija el tema visual de la aplicación.
Landing Page: Una página de presentación pública (www.tmsgaval.com) con información del producto y el botón para ir al "Login".

🚀 Parte 3: Mejoras y Siguientes Pasos Recomendados (Mi Aporte Estratégico)

Refinamiento de KPIs:
Filtros Avanzados en Dashboards: Añadir filtros por vehículo, por tipo de OT, por rango de KM, etc., a todos los dashboards para un análisis más granular.
Dashboard Comparativo (Superadmin): Crear una vista exclusiva para el Superadmin que compare los KPIs clave (Disponibilidad, $/KM) entre las diferentes empresas cliente.
Automatización y Notificaciones:
Alertas por Correo Electrónico: Enviar notificaciones automáticas cuando una pauta de mantenimiento esté próxima a vencerse o ya esté vencida.
Integración con GPS (si aplica): Crear un proceso para actualizar el kilometraje de los vehículos automáticamente desde un proveedor de GPS, en lugar de hacerlo manualmente.
Gestión de Inventario:
Control de Stock de Insumos: Añadir un campo stock al modelo Insumo y descontar automáticamente la cantidad cada vez que se usa en una OT.
Alertas de Stock Bajo: Notificar cuando el stock de un insumo crítico esté por debajo de un umbral mínimo.
Preparación para Producción (Fase 3 que habíamos discutido):
Configuración de Entorno de Producción: Ajustar settings.py (ej. DEBUG = False), configurar un servidor de aplicaciones (Gunicorn) y un servidor web (Nginx).
Gestión de Archivos Estáticos y de Medios: Configurar un servicio como Amazon S3 para almacenar los PDFs de las pautas y otros archivos subidos por los usuarios.
Seguridad Avanzada: Implementar HTTPS con un certificado SSL, configurar CORS, y revisar todas las medidas de seguridad de Django.