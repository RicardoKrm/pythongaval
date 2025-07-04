Resumen de Necesidades del Cliente (Extraído de las Conversaciones)
Estas son las funcionalidades y reglas de negocio clave que el cliente ha definido:
1. Gestión de Órdenes de Trabajo (OT) y Jerarquía
Creación de OT por Tipo:
Correctiva (OTC) y Evaluativa (OTE): Deben solicitar un "Tipo de Falla" (Crítica, Mediana, Leve) que defina la prioridad.
Evaluativa (OTE): Debe tener campos para "Síntomas" y seguir un flujo: Prueba de Ruta -> Diagnóstico -> Aplicar Corrección.
Preventiva (OTP): Basada en "Pautas" de mantenimiento predefinidas.
Sistema de Jerarquía y Permisos (CRÍTICO):
Roles: Hay roles claros con distintos poderes (Dueño > Administrador > Mecánico).
Pausa de OT: Solo el Administrador puede pausar una OT. El mecánico debe solicitarlo.
Alertas por Pausa: Cuando un Administrador pausa una OT, el sistema DEBE enviar una alerta automática al superior (Dueño/Gerente) indicando el motivo. Esto es para asegurar que los problemas se escalen y no queden olvidados.
Autorización para Modificar: Cualquier modificación a una OT una vez que su "cronómetro" ha comenzado (cambiar tareas, reasignar mecánico, etc.) requiere autorización de un superior y debe dejar un registro ("acusete").
Autorización para Horas Extra: Si una tarea excede su tiempo estándar (ej. 5 horas de pauta), el cronómetro no sigue corriendo indefinidamente. Para trabajar horas extra, el Administrador debe autorizarlo explícitamente en el sistema. Si no hay autorización, la OT queda pausada/bloqueada al finalizar el día.
2. Gestión de Repuestos (Inventario)
Carga de Repuestos a OT: Desde la OT, debe haber un botón para abrir una ventana emergente (modal) y añadir repuestos.
Buscador Inteligente: La ventana emergente debe tener un buscador que filtre el inventario en tiempo real al escribir.
Detalle del Repuesto: El sistema debe manejar códigos de repuesto complejos que indican su calidad (Original, Alternativo, etc.). Al mecánico se le muestra el código y la cantidad disponible, pero no el precio de costo.
Panel Dedicado ("Pizarra de Repuestos"): El cliente quiere que la gestión de inventario no esté "escondida", sino que tenga su propio panel o "pizarra" en el menú principal para darle más visibilidad y valor percibido al producto.
3. Módulo de Control de Combustible
Panel Dedicado: Crear una nueva "Pizarra de Combustible".
Cálculo de Rendimiento: El KPI principal es el rendimiento (Km/L).
Semáforo Visual: Implementar un "semáforo" (rojo, amarillo, verde) que compare el rendimiento actual de un vehículo contra un estándar óptimo o su propio promedio histórico.
Análisis por Factores: Poder visualizar cómo el rendimiento se ve afectado por la ruta u otros factores.
4. KPIs de Recursos Humanos (Técnicos y Administrador)
KPI de Productividad del Equipo Técnico:
Cálculo: Comparar Total de Horas Disponibles vs. Total de Horas Utilizadas por el equipo de mecánicos en un período, expresado en porcentaje (ej: "Utilización del 120%").
Horas Disponibles Dinámicas: El total de horas disponibles debe ser configurable (ej. 40, 44 horas/semana) y debe ajustarse automáticamente según los feriados y el día del mes en que se consulta.
Tiempos Estándar: El sistema debe conocer el tiempo estándar de cada pauta de mantenimiento (ej: la pauta "SM1" dura 5 horas) para poder hacer los cálculos.
KPI de Cumplimiento del Administrador:
Cálculo: Medir el porcentaje de cumplimiento de la programación semanal que hizo el administrador.
Objetivo: Permitir al "Dueño" ver si el administrador está cumpliendo con lo planificado, si va adelantado o atrasado, para poder identificar cuellos de botella (falta de recursos, personal, vehículos, etc.).
5. Visión del Superadministrador (Multi-Tenant y Business Intelligence)
Panel Agregado: El Superadministrador (tú) necesita un panel totalmente separado donde pueda ver datos agregados y comparativos de TODOS sus clientes.
Inteligencia de Mercado: El objetivo es hacer análisis de mercado: comparar costos de repuestos entre clientes, ver qué proveedores son más económicos, comparar la eficiencia de diferentes flotas, etc. Esta información es para ti y no debe ser visible para los clientes individuales.
Comparación con la Pauta Inicial: ¿Qué está hecho y qué falta?
Ahora, contrastemos tus "Funcionalidades Completadas (✓✓✓)" con lo que el cliente realmente necesita según las conversaciones.
Pizarra mant. (Pizarra de Mantenimiento): ✓✓✓
Tu Pauta: "Dashboard principal está completo, mostrando estado de la flota, próximos mantenimientos y KPIs de costos".
Verificación: La base visual está. Sin embargo, la conversación revela que para que sea funcional, necesita estar conectada a la lógica de prioridades (Crítica/Mediana/Leve) y a los estados de OT (Pausada, En Proceso, etc.) que se definen en la gestión de OT. Falta la integración de estas reglas de negocio.
Panel OT (Panel de Órdenes de Trabajo): ✓✓✓
Tu Pauta: "Gestión de OTs es robusta. Se pueden asignar tareas desde un catálogo Excel".
Verificación: Esta es el área con la mayor brecha. La base de crear una OT puede estar, pero las conversaciones revelan que falta toda la lógica crítica de negocio: el sistema de jerarquía, los permisos por rol, las alertas automáticas, la pausa controlada por el administrador y, fundamentalmente, la autorización de horas extra y modificaciones. El módulo, como lo describe el cliente, está lejos de estar completo.
Pizarra PROG. (Pizarra de Programación): ✓✓✓
Tu Pauta: "Calendario funcional: muestra OTs, reprograma con drag-and-drop, visualiza disponibilidad de repuestos".
Verificación: La funcionalidad básica de la librería del calendario (FullCalendar probablemente) está implementada. Sin embargo, la conversación añade una necesidad clave: el KPI de Cumplimiento del Administrador. El calendario no solo debe mostrar eventos, sino que debe medir y reportar el cumplimiento de esa programación. Esta capa de análisis falta por completo.
Inventario de Repuestos: ✓✓✓
Tu Pauta: "Carga masiva desde Excel, lógica update_or_create, descarga de plantilla".
Verificación: La gestión de la base de datos de repuestos está. Sin embargo, el cliente define dos requisitos clave que faltan:
La ventana emergente con buscador para añadir repuestos a una OT.
La creación de una "Pizarra de Repuestos" separada en el menú principal.
La funcionalidad está a nivel de backend, pero falta la integración y la interfaz que el cliente espera usar.
Control-Comb. (Control de Combustible): ✓✓✓
Tu Pauta: "Pizarra de análisis, página de registro, cálculo de rendimiento (Km/L), predicciones".
Verificación: Parece que esta es la funcionalidad más alineada. Tienes la base. Lo que el cliente añade y que falta es el "pulido final": la implementación del semáforo de rendimiento visual y el análisis de cómo la ruta afecta el consumo.
KPI FLOTA (OTC, OTP, OTE): ✓✓✓
Tu Pauta: "El dashboard ya calcula y muestra la cantidad de OTs preventivas y correctivas".
Verificación: Los contadores básicos están. Pero la conversación define un KPI de RR.HH. extremadamente detallado y complejo (productividad del equipo, cumplimiento del admin) que no se menciona en tu pauta y que falta por completo. Este es un módulo entero por construir.
Análisis Flota / Graf. Pareto y Costos y Tendencias: ✓✓✓
Tu Pauta: "Análisis de fallas (Pareto) y TCO/costo por KM están implementados".
Verificación: Las estructuras de los gráficos están. Sin embargo, su precisión depende de que todos los módulos anteriores funcionen con las reglas de negocio correctas (ej. costos reales de repuestos, horas hombre justificadas, etc.). Están visualmente, pero su utilidad real depende de la implementación de todo lo demás.
Conclusión del Análisis
Tu pauta inicial describe un proyecto donde las estructuras de datos y las interfaces básicas están construidas, lo cual es un gran avance.
Sin embargo, las conversaciones con el cliente revelan que el verdadero valor del software reside en la lógica de negocio, las automatizaciones, las jerarquías de permisos y los análisis profundos. La gran mayoría de estas reglas críticas aún no están implementadas.